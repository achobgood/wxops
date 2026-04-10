# Executive/Assistant Pairing Migration

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM-to-Webex migration pipeline gap — executive/assistant (boss/admin) relationships

---

## 1. Problem Statement

CUCM executive/assistant relationships (also called "boss/admin" or "manager/assistant" pairings) are not discovered, normalized, mapped, analyzed, or migrated by the current pipeline. This is a **critical enterprise feature gap** — executives will notice on day 1 if their assistant can no longer pick up, screen, filter, or place calls on their behalf.

### What the feature does

In both CUCM and Webex Calling, executive/assistant is a call routing and delegation feature:

- **Executive** designates one or more assistants who can answer, screen, and place calls on their behalf.
- **Assistant** can opt in/out of handling calls for each executive in their pool.
- Incoming calls to the executive ring the assistant(s) — sequentially or simultaneously.
- Call filtering rules control which calls reach the assistant vs. go directly to voicemail or another destination.
- Screening settings control how the assistant is alerted (ring splash, silent).
- The assistant can forward filtered calls to a specific number.

### Current pipeline state

- **Discovery:** The `UserExtractor` pulls the `manager` field from EndUser records, but this is CUCM's HR-style manager — not the telephony executive/assistant service config. The actual executive/assistant service configuration lives in CUCM's user service profile assignments, not in the user record.
- **Normalization:** No normalizer handles executive/assistant relationships.
- **Mapping:** No mapper produces executive/assistant pairing objects.
- **Analysis:** No analyzer detects executive/assistant configurations that need decisions.
- **Advisory:** No advisory pattern flags environments with executive/assistant usage.
- **Report:** The assessment report does not mention executive/assistant pairs.
- **Execution:** No executor configures executive/assistant settings in Webex.

### Impact of not migrating

Executives in enterprises of any size rely on this feature daily. On migration day, if the pairing is not configured:

1. Calls ring the executive's phone directly instead of routing through the assistant.
2. The assistant loses the ability to answer, screen, or place calls on behalf of the executive.
3. Call filtering rules (e.g., "only internal calls to assistant") are lost.
4. The executive's alerting preferences (sequential vs. simultaneous, rollover behavior) are lost.

This is a **high-visibility failure** because the affected users are typically senior leadership.

---

## 2. CUCM Source Data

### 2a. AXL Discovery

Executive/assistant relationships in CUCM are configured through the **Executive Mobility** service (also called "Executive-Assistant" service). The data is spread across several CUCM objects:

#### Service Profile Assignment

Each user with executive or assistant capability has a **User Service Profile** that enables the Executive or Executive-Assistant service. The relevant AXL queries:

```
listEndUser → getEndUser:
  - serviceProfile (FK to Service Profile)
  - associatedDevices
  - enableCti
```

```
getServiceProfile:
  - name
  - subscribedServices (list of subscribed BroadSoft-style services)
```

However, CUCM's executive/assistant is actually configured at the **line/DN level**, not the user level. The AXL objects are:

#### Direct AXL Queries Needed

**1. SQL query for executive/assistant assignments:**

```sql
SELECT eu.userid, eu.pkid as user_pkid, 
       ea.fkexecutive, ea.fkassistant,
       exec_user.userid as executive_userid,
       asst_user.userid as assistant_userid
FROM executiveassistant ea
JOIN enduser eu ON eu.pkid = ea.fkexecutive
JOIN enduser exec_user ON exec_user.pkid = ea.fkexecutive
JOIN enduser asst_user ON asst_user.pkid = ea.fkassistant
```

This is the authoritative table. CUCM stores executive/assistant relationships in the `executiveassistant` database table.

**2. User service subscriptions (to identify who has the service enabled):**

```sql
SELECT eu.userid, s.name as service_name, s.servicetype
FROM enduser eu
JOIN endusersubscribedservice euss ON euss.fkenduser = eu.pkid
JOIN subscribedservice s ON s.pkid = euss.fksubscribedservice
WHERE s.name IN ('Executive', 'Executive-Assistant')
```

**3. Executive call filtering/screening settings** are stored at the user level in CUCM and are not exposed via standard AXL `getEndUser`. They require the `executeSQLQuery` approach or direct device/line inspection for:
- `callFilterEnabled` — whether filtering is active
- `filterType` — ALL_CALLS, INTERNAL_ONLY, EXTERNAL_ONLY, CUSTOM
- `screeningEnabled` — whether call screening is active

### 2b. Raw Data Shape

The extractor should produce:

```python
raw_data["features"]["executive_assistant_pairs"] = [
    {
        "executive_userid": "jsmith",
        "assistant_userid": "jdoe", 
        "executive_pkid": "...",
        "assistant_pkid": "...",
    },
    ...
]

raw_data["features"]["executive_settings"] = [
    {
        "userid": "jsmith",
        "role": "EXECUTIVE",  # or "EXECUTIVE_ASSISTANT"
        "filter_enabled": True,
        "filter_type": "ALL_CALLS",
        "screening_enabled": True,
        "alerting_mode": "SIMULTANEOUS",
    },
    ...
]
```

### 2c. Extraction Implementation

Add extraction to `src/wxcli/migration/cucm/extractors/features.py` (the `FeatureExtractor` class). The executive/assistant data requires SQL queries since AXL does not expose `listExecutiveAssistant` / `getExecutiveAssistant` operations.

New methods on `FeatureExtractor`:
- `_extract_executive_assistant_pairs(result)` — SQL join across `executiveassistant`, `enduser`
- `_extract_executive_settings(result)` — SQL query for user service subscriptions + executive config

Add the results to `self.results["executive_assistant_pairs"]` and `self.results["executive_settings"]`.

---

## 3. Webex Target APIs

### 3a. Executive Assistant Type Assignment

**Endpoint:** `PUT /people/{personId}/features/executiveAssistant`

```json
{
  "type": "EXECUTIVE"  // or "EXECUTIVE_ASSISTANT" or "UNASSIGNED"
}
```

**Scope:** `spark-admin:people_write`

This is the first step — designate who is an executive and who is an assistant. Both the executive and each assistant must have this set before pairing.

### 3b. Assign Assistants to Executive

**Endpoint:** `PUT /telephony/config/people/{personId}/executive/assignedAssistants`

```json
{
  "allowOptInEnabled": true,
  "assistants": [
    {
      "id": "Y2lzY29...",  // Webex person ID of assistant
      "optInEnabled": true
    }
  ]
}
```

**Scope:** `spark-admin:telephony_config_write`

### 3c. Configure Executive Alert Settings

**Endpoint:** `PUT /telephony/config/people/{personId}/executive/alert`

```json
{
  "alertingMode": "SIMULTANEOUS",
  "nextAssistantNumberOfRings": 3,
  "rolloverEnabled": true,
  "rolloverAction": "VOICE_MESSAGING",
  "rolloverWaitTimeInSecs": 20,
  "clidNameMode": "EXECUTIVE_ORIGINATOR",
  "clidPhoneNumberMode": "EXECUTIVE"
}
```

**Scope:** `spark-admin:telephony_config_write`

### 3d. Configure Executive Call Filtering

**Endpoint:** `PUT /telephony/config/people/{personId}/executive/callFiltering`

```json
{
  "enabled": true,
  "filterType": "ALL_CALLS"
}
```

**Scope:** `spark-admin:telephony_config_write`

Filter types: `CUSTOM_CALL_FILTERS`, `ALL_CALLS`, `ALL_INTERNAL_CALLS`, `ALL_EXTERNAL_CALLS`

### 3e. Configure Executive Screening

**Endpoint:** `PUT /telephony/config/people/{personId}/executive/screening`

```json
{
  "enabled": true,
  "alertType": "RING_SPLASH"
}
```

**Scope:** `spark-admin:telephony_config_write`

### 3f. Configure Assistant Settings

**Endpoint:** `PUT /telephony/config/people/{personId}/executive/assistant`

```json
{
  "forwardFilteredCallsEnabled": true,
  "forwardToPhoneNumber": "+14155551234",
  "executives": [
    {
      "personId": "Y2lzY29...",
      "optInEnabled": true
    }
  ]
}
```

**Scope:** `spark-admin:telephony_config_write`

### 3g. API Execution Order

The APIs must be called in this order:

1. Set type to `EXECUTIVE` on the executive person
2. Set type to `EXECUTIVE_ASSISTANT` on each assistant person
3. Assign assistants to the executive (3b)
4. Configure alert settings on the executive (3c)
5. Configure call filtering on the executive (3d)
6. Configure screening on the executive (3e)
7. Configure assistant settings on each assistant (3f)

Steps 4-7 can run in parallel after step 3 completes.

---

## 4. Pipeline Integration

### 4a. Normalization (Phase 04)

Add two new normalizer functions in `transform/normalizers.py`:

```python
def normalize_executive_assistant_pair(raw: dict) -> MigrationObject:
    """Normalize an executive/assistant relationship pair."""

def normalize_executive_settings(raw: dict) -> MigrationObject:
    """Normalize executive/assistant user settings."""
```

Register in `RAW_DATA_MAPPING`:
```python
("features", "executive_assistant_pairs", "normalize_executive_assistant_pair"),
("features", "executive_settings", "normalize_executive_settings"),
```

Object types in the store: `"executive_assistant_pair"` and `"executive_settings"`.

### 4b. Cross-References (Phase 04)

Add to `CrossReferenceBuilder`:

- `executive_has_assistant` — executive user canonical_id -> assistant user canonical_id
- `assistant_serves_executive` — reverse of above
- `user_is_executive` — user -> executive_settings object
- `user_is_assistant` — user -> executive_settings object

### 4c. Mapping (Phase 05)

Create a new mapper: `src/wxcli/migration/transform/mappers/executive_assistant_mapper.py`

**Class:** `ExecutiveAssistantMapper`
- `name = "executive_assistant_mapper"`
- `depends_on = ["user_mapper"]`

The mapper:
1. Reads all `executive_assistant_pair` objects from the store
2. Resolves executive and assistant user canonical_ids via cross-refs
3. Produces `CanonicalExecutiveAssistant` objects (one per executive, with list of assistant IDs)
4. Enriches executive users with `executive_settings` (alerting mode, filtering config, screening)
5. Enriches assistant users with `assistant_settings` (forward filtered calls config)

**New canonical model** (add to `models.py`):

```python
class CanonicalExecutiveAssistant(MigrationObject):
    """Executive/assistant pairing for migration."""
    executive_canonical_id: str
    assistant_canonical_ids: list[str]
    alerting_mode: str  # "SEQUENTIAL" or "SIMULTANEOUS"
    filter_enabled: bool
    filter_type: str  # "ALL_CALLS", etc.
    screening_enabled: bool
```

**Decisions produced:**
- If the assistant user is not being migrated (e.g., already in Webex, or excluded), produce a `MISSING_DATA` decision with context explaining the broken pairing.
- If the executive user is not being migrated, same treatment.

### 4d. Analysis (Phase 06)

No new analyzer needed for the basic case. The `MissingDataAnalyzer` will catch cases where one side of the pairing is missing. However, consider adding detection in `FeatureApproximationAnalyzer` if executive/assistant settings have CUCM-specific nuances that don't map 1:1.

### 4e. Execution (Phase 07)

The planner (`execute/planner.py`) produces operations for executive/assistant configuration:

1. `executive_type_assign` — set EXECUTIVE type on person
2. `assistant_type_assign` — set EXECUTIVE_ASSISTANT type on person
3. `executive_assign_assistants` — pair assistants to executive
4. `executive_configure_alert` — set alert settings
5. `executive_configure_filtering` — set call filtering
6. `executive_configure_screening` — set screening
7. `assistant_configure_settings` — set assistant forward/opt-in settings

**Dependency edges:**
- `executive_type_assign` depends on `user:create` for the executive
- `assistant_type_assign` depends on `user:create` for the assistant
- `executive_assign_assistants` depends on both type assignments
- Steps 4-7 depend on `executive_assign_assistants`

---

## 5. Report Changes

### 5a. Assessment Report — Executive Summary (Page 2)

In the "Environment Inventory" section, add a row:

| Metric | Value |
|--------|-------|
| Executive/Assistant Pairs | N |

### 5b. Assessment Report — Technical Appendix

Add a new subsection "Executive/Assistant Pairings" in the call settings area:

- Table of executives with their assigned assistants
- Alerting mode (sequential/simultaneous) per executive
- Call filtering configuration per executive
- Any broken pairings (executive or assistant not in migration scope)

### 5c. Implementation

Modify `src/wxcli/migration/report/executive.py`:
- In `generate_executive_summary()`, add exec/assistant pair count to the environment inventory table.

Modify `src/wxcli/migration/report/appendix.py`:
- Add an executive/assistant section after the call settings section.
- Query the store for `executive_assistant_pair` objects and render a summary table.

---

## 6. Advisory Pattern

### 6a. New Cross-Cutting Pattern: Executive/Assistant Migration Complexity

Add to `advisory_patterns.py`:

**Pattern name:** `executive_assistant_migration`
**Category:** `migrate_as_is` (if both sides present) or `out_of_scope` (if one side missing)
**Severity:** `HIGH` (when pairs detected), `INFO` (when none detected)

**Logic:**
1. Count all `executive_assistant_pair` objects in the store
2. Check that both executive and assistant users are in migration scope
3. If any pairs have a user outside scope, flag as HIGH with detail explaining which side is missing
4. If all pairs are complete, flag as MEDIUM informational: "N executive/assistant pairings detected. These will be migrated automatically. Verify alerting mode preferences post-migration."

**Finding detail includes:**
- Count of complete pairs
- Count of broken pairs (one side not in scope)
- List of affected executive names
- Recommendation: complete pairs migrate as-is; broken pairs need manual Webex configuration or scope expansion

### 6b. Recommendation Rule

Add to `recommendation_rules.py` for any `MISSING_DATA` decisions that reference executive/assistant context:

If `context.get("missing_reason") == "executive_assistant_broken_pair"`:
- Recommend `"skip"` if the missing side is permanently excluded
- Return `None` (force human review) if the missing side might be added later

---

## 7. Documentation Updates Required

Every file listed below needs specific updates after implementation. This is the complete list.

### 7a. CLAUDE.md Files

| File | Section | What to Add |
|------|---------|-------------|
| `/CLAUDE.md` (root) | File Map > Migration Knowledge Base | No change needed unless a new KB doc is created |
| `src/wxcli/migration/CLAUDE.md` | File Map table | Add `executive_assistant_mapper.py` to mappers list |
| `src/wxcli/migration/CLAUDE.md` | Pipeline Commands | No change (commands unchanged) |
| `src/wxcli/migration/transform/CLAUDE.md` | Pass 1: Normalizers section | Add `normalize_executive_assistant_pair` and `normalize_executive_settings` to key normalizers list |
| `src/wxcli/migration/transform/CLAUDE.md` | CrossReferenceBuilder table | Add `executive_has_assistant`, `assistant_serves_executive`, `user_is_executive`, `user_is_assistant` relationships |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Mapper Inventory > Tier 3 table | Add `ExecutiveAssistantMapper` row |
| `src/wxcli/migration/cucm/CLAUDE.md` | Extraction Order / raw_data Structure | Document `executive_assistant_pairs` and `executive_settings` keys |
| `src/wxcli/migration/advisory/CLAUDE.md` | Cross-Cutting Advisory Patterns list | Add Pattern N: Executive/Assistant Migration Complexity |
| `src/wxcli/migration/report/CLAUDE.md` | (if it exists) | Add executive/assistant section to report structure |

### 7b. Reference Docs

| File | Section | What to Add |
|------|---------|-------------|
| `docs/reference/person-call-settings-permissions.md` | Section 4: Executive/Assistant Settings | Already documented. No changes needed unless new API behaviors discovered during implementation. |

### 7c. Knowledge Base

| File | Section | What to Add |
|------|---------|-------------|
| `docs/knowledge-base/migration/kb-user-settings.md` | New section or existing call settings section | Add executive/assistant mapping rules: CUCM service subscription to Webex type assignment, alerting mode mapping, call filtering mapping |
| `docs/knowledge-base/migration/kb-feature-mapping.md` | Feature mapping table | Add row: "Executive/Assistant" -> "Executive/Assistant (native)" with notes on API ordering requirement |

### 7d. Runbooks

| File | Section | What to Add |
|------|---------|-------------|
| `docs/runbooks/cucm-migration/operator-runbook.md` | Pipeline stages section (map phase) | Mention executive/assistant mapper in the mapping stage description |
| `docs/runbooks/cucm-migration/decision-guide.md` | Decision type entries | Add entry for MISSING_DATA decisions with `executive_assistant_broken_pair` context |
| `docs/runbooks/cucm-migration/tuning-reference.md` | Config keys section | Add any config keys for executive/assistant migration behavior |

### 7e. Skills

| File | Section | What to Add |
|------|---------|-------------|
| `.claude/skills/cucm-migrate/SKILL.md` | No structural change needed | The skill delegates to mappers/executors; new mapper is auto-discovered |

### 7f. Models

| File | What to Add |
|------|-------------|
| `src/wxcli/migration/models.py` | `CanonicalExecutiveAssistant` class (or extend `MigrationObject` usage) |

---

## 8. Test Strategy

### 8a. Unit Tests — Extractor

**File:** `tests/migration/cucm/test_executive_assistant_extractor.py`

| Test | Description |
|------|-------------|
| `test_extract_pairs_basic` | Mock SQL query returns 2 pairs, verify raw_data shape |
| `test_extract_pairs_empty` | No executive/assistant rows, verify empty list |
| `test_extract_settings_executive` | User with Executive service, verify role and settings |
| `test_extract_settings_assistant` | User with Executive-Assistant service |
| `test_extract_sql_fallback` | Verify SQL query runs correctly when AXL methods unavailable |

### 8b. Unit Tests — Normalizer

**File:** `tests/migration/transform/test_normalizers_executive.py`

| Test | Description |
|------|-------------|
| `test_normalize_pair` | Raw pair dict -> MigrationObject with correct canonical_id |
| `test_normalize_settings_executive` | Executive settings normalization |
| `test_normalize_settings_assistant` | Assistant settings normalization |

### 8c. Unit Tests — Mapper

**File:** `tests/migration/transform/mappers/test_executive_assistant_mapper.py`

| Test | Description |
|------|-------------|
| `test_map_basic_pair` | One executive + one assistant, verify CanonicalExecutiveAssistant produced |
| `test_map_multi_assistant` | Executive with 3 assistants |
| `test_map_broken_pair_missing_executive` | Assistant present, executive not in scope -> MISSING_DATA decision |
| `test_map_broken_pair_missing_assistant` | Executive present, assistant not in scope -> MISSING_DATA decision |
| `test_map_settings_sequential` | CUCM sequential alerting -> Webex SEQUENTIAL |
| `test_map_settings_simultaneous` | CUCM simultaneous alerting -> Webex SIMULTANEOUS |
| `test_map_filtering_all_calls` | Call filtering type mapping |
| `test_map_no_pairs` | No executive/assistant data -> no objects produced |

### 8d. Unit Tests — Advisory Pattern

**File:** `tests/migration/advisory/test_advisory_executive_assistant.py`

| Test | Description |
|------|-------------|
| `test_pattern_fires_with_pairs` | Store has executive/assistant pairs -> advisory produced |
| `test_pattern_silent_no_pairs` | No pairs -> empty findings |
| `test_pattern_broken_pair_high_severity` | One side missing -> HIGH severity |
| `test_pattern_complete_pairs_medium` | All pairs complete -> MEDIUM informational |

### 8e. Integration Tests

**File:** `tests/migration/transform/test_executive_assistant_integration.py`

| Test | Description |
|------|-------------|
| `test_full_pipeline_with_exec_assistant` | Discover -> normalize -> map -> analyze with executive/assistant data |
| `test_report_includes_exec_assistant` | Assessment report includes executive/assistant section |

### Estimated test count: 18-22 tests

---

## 9. Risks and Open Questions

### 9a. CUCM Version Variability

The `executiveassistant` SQL table structure may vary across CUCM versions (10.x, 11.x, 12.x, 14.x, 15.x). Need to verify the SQL schema against the earliest supported version.

**Mitigation:** Test SQL queries against the existing testbed (CUCM 15.0). Add a try/except fallback if the table doesn't exist (older CUCMs without this feature).

### 9b. Service Profile vs. Direct Configuration

In some CUCM deployments, executive/assistant is configured via User Service Profiles (UC Services) rather than direct line-level configuration. The SQL approach should capture both paths.

**Mitigation:** Query both the `executiveassistant` table and the `endusersubscribedservice` table to get a complete picture.

### 9c. Large-Scale Executive Pools

Some enterprises have executives with 5+ assistants (C-suite with a pool of admins). Webex supports this but the API requires individual assistant assignment. No batch endpoint exists.

**Mitigation:** The executor should iterate over assistants and make individual API calls. Rate limiting is unlikely to be an issue for typical volumes (< 100 executives per org).

### 9d. Cross-Location Pairing

An executive in one CUCM location may have an assistant in another. This maps naturally to Webex (no location restriction on executive/assistant pairing) but should be verified.

### 9e. Webex Prerequisite: Calling License

Both the executive and assistant must have a Webex Calling Professional license for the executive/assistant feature to work. Basic license does not include it. The mapper should check the license tier and flag if Basic.

---

## 10. Effort Estimate

| Component | Estimated Lines | Effort |
|-----------|----------------|--------|
| Extractor (SQL queries) | ~80 | Small |
| Normalizers (2 functions) | ~50 | Small |
| Cross-reference additions | ~30 | Small |
| Mapper (new file) | ~180 | Medium |
| Advisory pattern | ~60 | Small |
| Report changes | ~40 | Small |
| Tests (18-22) | ~500 | Medium |
| Doc updates (8 files) | ~200 | Small-Medium |
| **Total** | **~1140** | **Medium** |

Estimated implementation time: 1-2 sessions.
