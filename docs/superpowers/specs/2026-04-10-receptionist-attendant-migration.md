# Receptionist / Attendant Console Migration

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM-to-Webex migration pipeline gap -- receptionist and attendant console user workflows

---

## 1. Problem Statement

CUCM receptionists use Cisco Unified Attendant Console (CUAC) or phone-based attendant workflows with 20+ monitored lines, directory search, and rapid call transfer. These are the most phone-dependent users in the enterprise -- their entire workflow revolves around physical phone layout (BLF fields, line appearances, speed dials) and fast call handling patterns.

Webex Calling has two distinct receptionist features that replace this workflow:
1. **Receptionist Client** -- per-person monitored member list (API: `/people/{id}/features/reception`)
2. **Receptionist Contact Directories** -- per-location named directories (API: `/telephony/config/locations/{id}/receptionistContacts/directories`)

The current pipeline partially handles this through the `MonitoringMapper` (BLF entries become monitoring lists), but it **does not**:
- Detect which users are receptionists (vs. regular BLF users)
- Map CUAC application associations
- Create receptionist client configurations
- Create or populate receptionist contact directories
- Produce advisory patterns about receptionist workflow changes
- Surface receptionist-specific information in the assessment report

### What the feature does

#### CUCM Receptionist Workflow

In CUCM, receptionists typically operate with one or more of:

- **Cisco Unified Attendant Console (CUAC)** -- a Windows desktop application that provides directory search, call queue visibility, and drag-and-drop call transfer. CUAC connects via CTI and monitors line state for dozens of users.
- **Phone-based attendant** -- a physical IP phone with 10-48 BLF keys (often with Key Expansion Modules), configured via phone button templates with dedicated speed dials, BLF entries, and line appearances. The receptionist visually monitors line state on the phone's LED indicators.
- **CTI port/route point** -- receptionists using CUAC have associated CTI application devices that appear in CUCM as application users with `enableCti=True`.

Key behavioral characteristics of a CUCM receptionist:
- Monitors 10-50+ lines via BLF or CUAC
- Handles high call volume -- often the first point of contact for the organization
- Uses speed dials heavily for frequent transfers
- Depends on visual line state indicators (LED/BLF) for call handling decisions
- May have dedicated phone button templates with attendant-specific layouts
- Often assigned to the main DID/pilot number

#### Webex Receptionist Features

Webex Calling provides:

1. **Receptionist Client** (per-person):
   - Enables a person as a telephone attendant
   - Monitored member list (people and workspaces)
   - API: `GET/PUT /people/{personId}/features/reception`
   - Data model: `receptionEnabled` (bool) + `monitoredMembers` (list of person/workspace IDs)
   - SDK feature name is `receptionist` but API path is `reception`
   - Maximum member list not documented in the spec (needs verification)

2. **Receptionist Contact Directories** (per-location):
   - Named directories of users and location features (AA, CQ, HG, SNR, Paging)
   - API: CRUD at `/telephony/config/locations/{locationId}/receptionistContacts/directories`
   - Contact types: PEOPLE, AUTO_ATTENDANT, CALL_QUEUE, HUNT_GROUP, SINGLE_NUMBER_REACH, PAGING_GROUP
   - Directories have a name (1-40 chars) and a list of contacts (person IDs or feature IDs with type)
   - Scope: `spark-admin:telephony_config_write` / `spark-admin:telephony_config_read`

3. **Webex Receptionist Console App** -- a web-based client available to Webex Calling Professional licensed users that provides directory search, call status, and call handling. This is the closest equivalent to CUAC but works through the Webex client rather than a standalone Windows application.

### Current pipeline state

- **MonitoringMapper** (existing): Maps BLF entries to Webex monitoring lists per user. This captures *part* of the receptionist workflow -- the line monitoring portion. But monitoring lists and receptionist client settings are different features in Webex.
- **DeviceLayoutMapper** (existing): Captures the full phone button template layout including BLF keys, line appearances, and speed dials. This data is available but not connected to receptionist detection.
- **No receptionist detection**: The pipeline does not classify any user as a "receptionist" based on CUCM config signals.
- **No receptionist contact directory creation**: Location-level directories are not created during migration.
- **No advisory pattern**: No advisory pattern flags receptionist users for special handling.
- **Assessment report**: Does not mention receptionists or attendant console dependencies.

### Impact of not migrating

Receptionists notice immediately on day 1:
1. The CUAC desktop application stops working entirely -- it has no Webex equivalent executable.
2. Phone-based attendants lose their BLF layout (addressed partially by DeviceLayoutMapper, but the receptionist client feature itself is not enabled).
3. The receptionist cannot use directory search or drag-and-drop transfer from the old console.
4. If the main DID was routed through an attendant queue, calls may not reach the receptionist at all.

This is a **high-visibility failure** because the receptionist is often the first person callers encounter.

---

## 2. CUCM Source Data

### 2a. Detection Heuristics

There is no single `isReceptionist=True` flag in CUCM. Receptionists are detected by a combination of signals:

**Signal 1: High BLF Count (strongest signal)**

Users whose primary phone has 10+ BLF entries are likely receptionists or attendant-style users. The raw phone data is already extracted and available:

```python
# Already in store as phone:{name} objects
phone_data["busyLampFields"] = [
    {"blfDest": "1001", "blfDirn": "...", "label": "John Smith", "index": "1"},
    ...
]
```

Threshold: `len(phone_data["busyLampFields"]) >= 10` -- strong receptionist signal.

**Signal 2: Attendant Console Application User**

CUCM application users with `enableCti=True` that own CTI port or CTI route point devices are typically CUAC users. Currently, the pipeline's `UserExtractor` only pulls `endUser` records -- `applicationUser` records are not extracted.

```
listApplicationUser:
  - name
  - enableCti
  - associatedDevices → CTI port/route point names
```

If an application user's `associatedDevices` include devices whose names start with `CTI` or whose device type is `CTI Port` / `CTI Route Point`, this user is likely a CUAC attendant.

**Signal 3: Phone Button Template Name**

CUCM admins often name receptionist phone button templates with identifiable patterns:
- Contains "attendant", "reception", "lobby", "front desk", "operator"
- Template has an unusually high proportion of BLF keys vs. line keys

The `button_template` objects are already in the store. The template name is in `pre_migration_state.name`.

**Signal 4: Key Expansion Module (KEM) Presence**

Phones with KEM expansion modules (e.g., CP-8800-A-KEM, BEKEM, CP-CKEM-C) are strong receptionist signals -- regular users rarely need 36-72 additional keys. KEM presence is captured in the `CanonicalDeviceLayout.resolved_kem_keys` field.

**Signal 5: Main Number Assignment**

Users whose DN matches the location's main number are often receptionists. The `dn` objects are in the store, and the main number mapping happens during `LocationMapper`.

### 2b. No New AXL Extraction Required (mostly)

For Signals 1, 3, 4, and 5, all necessary data is already extracted by the existing pipeline:
- BLF counts: `phone:{name}` objects in the store
- Button template names: `button_template:{name}` objects
- KEM presence: `CanonicalDeviceLayout` objects (from DeviceLayoutMapper)
- Main number: `CanonicalLocation.main_number` (from LocationMapper)

**Signal 2 (application users) requires new extraction.** The `UserExtractor` would need a new `_extract_application_users(result)` method using `listApplicationUser` AXL call. This is optional and can be deferred -- Signals 1 + 3 + 4 cover the majority of receptionist detection without it.

### 2c. Proposed Raw Data Enhancement

For application user extraction (deferred, optional):

```python
raw_data["users"]["application_users"] = [
    {
        "name": "cuac_admin",
        "enableCti": True,
        "associatedDevices": ["CTIPRT-cuac_admin"],
        "associatedEndUsers": ["jdoe"],
    },
    ...
]
```

---

## 3. Webex Target APIs

### 3a. Person-Level Receptionist Client

**Read:** `GET /people/{personId}/features/reception`

```json
{
  "receptionEnabled": true,
  "monitoredMembers": [
    {
      "id": "Y2lzY29...",
      "displayName": "John Smith",
      "phoneNumber": "+12125551001",
      "extension": "1001"
    }
  ]
}
```

**Update:** `PUT /people/{personId}/features/reception`

```json
{
  "receptionEnabled": true,
  "monitoredMembers": ["<person-id-1>", "<person-id-2>", "..."]
}
```

**Scope:** `spark-admin:people_write` (update), `spark-admin:people_read` (read)

**SDK path mismatch:** The SDK feature name is `receptionist` but the API path segment is `reception`. This is documented in `person-call-settings-behavior.md` section 7.

**Validation:** `enabled` must not be `None`. If `monitoredMembers` is set, `enabled` must be `True`.

### 3b. Location-Level Receptionist Contact Directories

**Create:** `POST /telephony/config/locations/{locationId}/receptionistContacts/directories`

```json
{
  "name": "Main Reception Directory",
  "contacts": [
    {"personId": "Y2lzY29..."},
    {"featureId": "Y2lzY29...", "type": "AUTO_ATTENDANT"},
    {"featureId": "Y2lzY29...", "type": "CALL_QUEUE"}
  ]
}
```

**Response:** `{"id": "Y2lzY29..."}`

**List:** `GET /telephony/config/locations/{locationId}/receptionistContacts/directories`

Returns: `{"directories": [{"id": "...", "name": "...", "contacts": [...]}]}`

**Get:** `GET /telephony/config/locations/{locationId}/receptionistContacts/directories/{directoryId}`

**Update:** `PUT /telephony/config/locations/{locationId}/receptionistContacts/directories/{directoryId}`

**Delete:** `DELETE /telephony/config/locations/{locationId}/receptionistContacts/directories/{directoryId}`

**Contact types supported:** PEOPLE, AUTO_ATTENDANT, CALL_QUEUE, HUNT_GROUP, SINGLE_NUMBER_REACH, PAGING_GROUP

**Scope:** `spark-admin:telephony_config_write` / `spark-admin:telephony_config_read`

**Directory name limit:** 1-40 characters.

### 3c. Device-Level Hoteling (Related)

When receptionists use shared physical phones, the device-level hoteling settings are relevant:

**Modify:** `PUT /telephony/config/people/{personId}/devices/settings/hoteling`

```json
{
  "hoteling": {
    "enabled": true,
    "limitGuestUse": true,
    "guestHoursLimit": 12
  }
}
```

This applies when the receptionist's device is also used as a hoteling host.

---

## 4. Pipeline Integration

### 4a. New: Receptionist Detector (in normalizer or post-mapper enrichment)

A new function that scores users for receptionist likelihood based on the signals from section 2a. This runs after all mappers have completed (it needs BLF counts, device layouts, and location main numbers).

**Proposed location:** New method on a `ReceptionistMapper` class in `src/wxcli/migration/transform/mappers/receptionist_mapper.py`.

**Dependencies:** `monitoring_mapper`, `device_layout_mapper`, `location_mapper`, `line_mapper`, `user_mapper`

**Algorithm:**

```python
def _score_receptionist_likelihood(self, store, user_cid, phone_data, layout):
    score = 0
    reasons = []
    
    blf_count = len(phone_data.get("busyLampFields") or [])
    if blf_count >= 20:
        score += 3
        reasons.append(f"{blf_count} BLF entries (20+)")
    elif blf_count >= 10:
        score += 2
        reasons.append(f"{blf_count} BLF entries (10+)")
    
    # KEM presence
    if layout and layout.resolved_kem_keys:
        score += 2
        reasons.append(f"KEM with {len(layout.resolved_kem_keys)} keys")
    
    # Template name signals
    template_name = (phone_data.get("phoneTemplateName") or "").lower()
    for keyword in ("attendant", "reception", "lobby", "operator", "front"):
        if keyword in template_name:
            score += 2
            reasons.append(f"Template name contains '{keyword}'")
            break
    
    # Main number assignment
    # (check if user's DN matches location main number)
    # score += 1 if match
    
    return score, reasons
    # Threshold: score >= 3 → likely receptionist
```

**Output:** For users scoring >= 3, the mapper produces:
1. A `CanonicalReceptionistConfig` object (new canonical type)
2. A `FEATURE_APPROXIMATION` decision if the receptionist has features that Webex cannot replicate (e.g., CUAC directory search, >50 monitored members)
3. Cross-refs: `user_has_receptionist_config`

### 4b. Enhance Existing MonitoringMapper

The `MonitoringMapper` already produces `CanonicalMonitoringList` objects from BLF entries. The enhancement:
- Add a `receptionist_candidate` flag to the monitoring list context
- When BLF count exceeds a threshold (e.g., 10), set `receptionist_candidate=True` in the monitoring list's `pre_migration_state`
- The ReceptionistMapper reads this flag as one of its signals

### 4c. New Advisory Pattern: Receptionist Workflow Change

**Pattern 21+ (next available number):** `detect_receptionist_workflow_impact`

```python
def detect_receptionist_workflow_impact(store: MigrationStore) -> list[AdvisoryFinding]:
    """Flag environments where receptionist/attendant console users require 
    special migration attention."""
```

**Fires when:** At least one user is detected as a receptionist candidate.

**Severity:** MEDIUM (receptionist workflow is significantly different, but the feature exists in Webex).

**Category:** `rebuild` -- CUAC-style workflows must be rebuilt using the Webex Receptionist Console app.

**Detail message template:**
```
{N} receptionist/attendant console user(s) detected. CUCM attendant console 
(CUAC) workflows do not have a direct Webex equivalent. Webex offers:
(1) Receptionist Client — per-person monitored member list via API
(2) Receptionist Contact Directories — per-location searchable directories
(3) Webex Receptionist Console — web-based call handling app

Receptionists will need training on the Webex Receptionist Console. Their 
monitored member lists will be migrated from BLF entries, but directory search, 
drag-and-drop transfer, and queue visibility require the new console app.
```

### 4d. Report Enhancement

Add a subsection to the assessment report's "User Migration" section:

**"Receptionist / Attendant Console Users"**
- Count of detected receptionist candidates
- For each: user name, location, BLF count, KEM presence, template name
- Feature gap summary: what works automatically vs. what needs manual setup
- Training recommendation for Webex Receptionist Console

### 4e. Execution Handler

New handler: `handle_receptionist_config_configure`

**API sequence:**
1. Enable receptionist client: `PUT /people/{personId}/features/reception`
   - `receptionEnabled: true`
   - `monitoredMembers: [list of resolved Webex person IDs from BLF→monitoring mapping]`
2. Create location receptionist contact directory (if not exists):
   `POST /telephony/config/locations/{locationId}/receptionistContacts/directories`
   - Name: derived from location name (e.g., "{Location} Reception Directory")
   - Contacts: all people at the location + any AA/CQ/HG features at the location

**Dependencies in planner:**
- Depends on: user creation, feature creation (AA/CQ/HG for directory contacts)
- Monitoring list members must already exist as Webex people

---

## 5. Migration Path

### 5a. What Maps Automatically

| CUCM Source | Webex Target | Mechanism |
|-------------|-------------|-----------|
| BLF entries on phone | Monitoring list members | MonitoringMapper (existing) |
| BLF entries on phone | Receptionist client monitored members | ReceptionistMapper (new) -- same source data, different Webex feature |
| Phone button template layout | Line key template | DeviceLayoutMapper (existing) |
| Speed dials | Speed dials on device | DeviceLayoutMapper (existing) |

### 5b. What Requires Manual Setup

| CUCM Feature | Webex Equivalent | Why Manual |
|-------------|-----------------|-----------|
| CUAC desktop application | Webex Receptionist Console (web) | Different application entirely -- requires user training |
| CUAC directory search | Receptionist Contact Directories | Directories must be created and populated with Webex IDs |
| CUAC call queue visibility | Webex Receptionist Console queue integration | Requires Webex Receptionist Console setup |
| CTI application user routing | No direct equivalent | CTI ports/route points don't exist in Webex |
| Custom attendant phone template with >48 BLF keys | Webex monitoring list (max 50) + Receptionist Contact Directories | Overflow entries go to directory, not monitoring list |

### 5c. What's Lost

| CUCM Feature | Notes |
|-------------|-------|
| CUAC Windows desktop app integration | No Webex equivalent -- must use web-based Receptionist Console |
| CTI-driven call routing through attendant | Webex uses standard call routing (AA/CQ) instead |
| Phone LED BLF indicators for >50 lines | Webex monitoring max is 50 members; KEM support depends on MPP model compatibility |
| Attendant queue pilot number routing | Must be rebuilt as Auto Attendant or Call Queue in Webex |

---

## 6. Data Model Changes

### 6a. New Canonical Type

```python
@dataclass
class CanonicalReceptionistConfig(MigrationObject):
    """Receptionist configuration detected from CUCM signals."""
    user_canonical_id: str = ""
    location_canonical_id: str = ""
    blf_count: int = 0
    has_kem: bool = False
    kem_key_count: int = 0
    template_name: str = ""
    detection_score: int = 0
    detection_reasons: list[str] = field(default_factory=list)
    monitored_members: list[str] = field(default_factory=list)  # canonical_ids
    is_main_number_holder: bool = False
```

### 6b. New DecisionType Value

No new `DecisionType` needed -- uses existing `FEATURE_APPROXIMATION` for cases where CUCM receptionist features exceed Webex capabilities.

### 6c. New Cross-Reference Types

- `user_has_receptionist_config` -- user → receptionist config
- `location_has_receptionist_directory` -- location → receptionist contact directory (created during execution)

---

## 7. Documentation Updates Required

### 7a. Reference Docs

- `docs/reference/person-call-settings-behavior.md` section 7 (Receptionist Client): Add migration context -- how BLF entries map to monitored members, maximum member count verification needed.
- `docs/reference/location-calling-core.md` or new section: Document Receptionist Contact Directories API (currently not covered in reference docs).

### 7b. Knowledge Base

- `docs/knowledge-base/migration/kb-user-settings.md`: Add receptionist/attendant console detection heuristics and Webex mapping.
- `docs/knowledge-base/migration/kb-feature-mapping.md`: Add CUAC → Webex Receptionist Console mapping.

### 7c. Runbooks

- `docs/runbooks/cucm-migration/decision-guide.md`: Add entry for receptionist-related FEATURE_APPROXIMATION decisions.
- `docs/runbooks/cucm-migration/operator-runbook.md`: Add receptionist migration workflow section.

### 7d. Migration CLAUDE.md

Update `src/wxcli/migration/CLAUDE.md` file map:
- Add `receptionist_mapper.py` to mapper inventory
- Update advisory pattern count
- Add canonical type to models

---

## 8. Open Questions

1. **Webex Receptionist Client maximum monitored members?** The API spec does not document a limit. The monitoring list max is 50 (enforced in MonitoringMapper). Does the receptionist client have the same limit? Needs live API verification.

2. **Receptionist Contact Directory maximum contacts?** The API spec does not document a limit. Needs live API verification.

3. **Should application user extraction be in scope?** Signal 2 (CUAC application users) requires new AXL extraction. The other 4 signals cover most cases. Recommend deferring application user extraction to a later phase.

4. **Detection threshold calibration.** The score >= 3 threshold in section 4a is a starting point. It should be validated against real CUCM environments during score calibration.

5. **Relationship to monitoring mapper.** The receptionist mapper reads the same BLF data as the monitoring mapper but produces different Webex configuration (receptionist client vs. monitoring list). Should the receptionist mapper *also* produce the monitoring list, or should it depend on the monitoring mapper's output? Recommendation: depend on monitoring mapper's output and produce only the receptionist-specific configuration.

---

## 9. Implementation Estimate

| Component | Effort | Notes |
|-----------|--------|-------|
| ReceptionistMapper class | Medium | New mapper, depends on 5 existing mappers |
| CanonicalReceptionistConfig model | Small | New dataclass in models.py |
| Advisory pattern (detect_receptionist_workflow_impact) | Small | Similar to existing patterns 17-20 |
| Report section | Small | Table of detected receptionists + gap summary |
| Execution handler | Medium | Two API calls per receptionist + directory creation |
| Tests | Medium | Detection scoring, mapper output, advisory pattern, handler |
| Reference doc updates | Small | Two docs need new sections |
| **Total** | **~3 days** | Can be parallelized with hoteling migration spec |
