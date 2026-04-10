# Voicemail Groups Migration

**Date:** 2026-04-10
**Status:** Spec
**Priority:** MEDIUM -- department shared voicemails lost during migration

---

## Problem Statement

CUCM Unity Connection supports shared voicemail mailboxes for departments -- typically reachable
via a hunt pilot (e.g., sales@, support@, billing@). These are **not personal voicemail** (which
the `VoicemailMapper` already handles). They are group-level voicemail destinations where:

- A hunt pilot or auto attendant forwards unanswered/overflow calls to a shared mailbox
- Multiple users can access and manage the shared mailbox
- The mailbox has its own extension, greeting, notification settings, and caller ID

During CUCM-to-Webex migration, these shared mailboxes are completely lost. The `FeatureMapper`
converts CUCM hunt pilots to Webex hunt groups or call queues, but the voicemail overflow
destination is not mapped. The `VoicemailMapper` only handles per-user voicemail profiles
(user_has_voicemail_profile cross-ref). There is no mapper, normalizer, or canonical model for
voicemail groups.

**Result:** After migration, calls that overflow from a hunt group or call queue ring
indefinitely or disconnect -- there is no shared voicemail to catch them. Department-level
voicemail messages (e.g., "You've reached the Sales team, please leave a message") are lost.
Notification workflows that forwarded voicemail-to-email for department mailboxes stop working.

**Scale:** A typical enterprise CUCM deployment has 5-15 shared voicemail mailboxes tied to
hunt groups, call queues, or auto attendants. Each mailbox may have custom greetings, email
notification chains, and fax reception configured.

---

## CUCM Source Data

### Unity Connection Shared Mailboxes

Unity Connection shared mailboxes are not directly extracted via AXL -- they are Unity
Connection objects. However, the CUCM-side configuration that *references* them is available:

**Hunt List → voiceMailUsage field:**
The `normalize_hunt_list` normalizer already extracts `voice_mail_usage` from the hunt list:
```python
"voice_mail_usage": raw.get("voiceMailUsage"),  # normalizers.py line 704
```

The `FeatureMapper` already checks this field:
```python
hunt_list_state.get("voiceMailUsage", "NONE") != "NONE",  # feature_mapper.py line 426
```

This flag indicates whether a hunt list forwards to voicemail on overflow. Values:
- `NONE` -- no voicemail overflow
- `USE_PERSONAL_PREFERENCE` -- use each user's personal VM settings
- `USE_PILOT_NUMBER` -- forward to a shared voicemail pilot

**Hunt Pilot → voiceMailProfileName:**
The hunt pilot's voicemail profile, if set, links to a Unity Connection shared mailbox.
This field is in the raw AXL data but not currently extracted by `normalize_hunt_pilot`.

**Unity Connection per-user VM settings:**
The `unity_connection.py` extractor retrieves per-user VM settings, but does not query
Unity Connection for shared/group mailbox configurations. This is a gap in the discovery
phase -- shared mailboxes require a separate Unity Connection API query.

### What We Have Today

| Data | Extracted? | Normalized? | Mapped? |
|------|-----------|-------------|---------|
| Hunt list voiceMailUsage flag | Yes | Yes | Checked but not acted on |
| Hunt pilot VM profile name | Partially | No | No |
| Unity Connection shared mailbox config | No | No | No |
| Shared mailbox greeting audio | No | N/A | N/A |
| Shared mailbox notification settings | No | N/A | N/A |

### What We Would Need to Extract

From Unity Connection REST API (`/vmrest/handlers/callhandlers`):

| Field | Description |
|-------|-------------|
| `DisplayName` | Mailbox display name (e.g., "Sales Voicemail") |
| `Extension` | Pilot extension for the mailbox |
| `DtmfAccessId` | Extension used for DTMF access |
| `GreetingRule` (Standard, AfterHours, etc.) | Active greeting configuration |
| `MessageRecipient` | List of users who receive messages from this mailbox |
| `NotificationRules` | Email/SMS notification configuration |
| `TransferRules` | Transfer-on-zero destination |

**Discovery gap:** The current `unity_connection.py` extractor queries `/vmrest/users/{id}/`
for per-user VM settings. It does not query `/vmrest/handlers/callhandlers` for shared
call handler (group voicemail) configurations. Adding this query is a prerequisite for
this feature.

---

## Webex Target APIs

Webex Calling has a **Voicemail Groups** feature at the location level. Verified in the
OpenAPI spec at `specs/webex-cloud-calling.json`.

### API Endpoints

| Operation | Method | Path | Scope |
|-----------|--------|------|-------|
| List all voicemail groups | GET | `/telephony/config/voicemailGroups` | `spark-admin:telephony_config_read` |
| Get voicemail group detail | GET | `/telephony/config/locations/{locationId}/voicemailGroups/{id}` | `spark-admin:telephony_config_read` |
| Create voicemail group | POST | `/telephony/config/locations/{locationId}/voicemailGroups` | `spark-admin:telephony_config_write` |
| Modify voicemail group | PUT | `/telephony/config/locations/{locationId}/voicemailGroups/{id}` | `spark-admin:telephony_config_write` |
| Delete voicemail group | DELETE | `/telephony/config/locations/{locationId}/voicemailGroups/{id}` | `spark-admin:telephony_config_write` |
| Available numbers (assignment) | GET | `/telephony/config/locations/{locationId}/voicemailGroups/availableNumbers` | `spark-admin:telephony_config_read` |
| Available fax numbers | GET | `/telephony/config/locations/{locationId}/voicemailGroups/faxMessage/availableNumbers` | `spark-admin:telephony_config_read` |

### Create Request Body (Required Fields)

From `PostLocationVoicemailGroupObject` schema:

```json
{
  "name": "Sales Voicemail",           // REQUIRED
  "extension": 5896,                    // REQUIRED
  "passcode": 1234,                     // REQUIRED
  "languageCode": "en_us",              // REQUIRED
  "messageStorage": {                   // REQUIRED
    "storageType": "INTERNAL"
  },
  "notifications": {                    // REQUIRED
    "enabled": true,
    "destination": "sales-team@example.com"
  },
  "faxMessage": {                       // REQUIRED
    "enabled": false
  },
  "transferToNumber": {                 // REQUIRED
    "enabled": false
  },
  "emailCopyOfMessage": {              // REQUIRED
    "enabled": false
  },
  "phoneNumber": "+16065551234",        // Optional
  "firstName": "Sales",                 // Deprecated, use directLineCallerIdName
  "lastName": "Team",                   // Deprecated, use directLineCallerIdName
  "directLineCallerIdName": {           // Optional
    "selection": "CUSTOM_NAME",
    "customName": "Sales Team"
  },
  "dialByName": "Sales Team"            // Optional
}
```

### Get Response (Full Object)

From `GetLocationVoicemailGroupObject` schema:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID of the voicemail group |
| `name` | string | Group name |
| `phoneNumber` | string | E.164 phone number (optional) |
| `extension` | number | Extension number |
| `routingPrefix` | string | Location routing prefix |
| `esn` | string | Enterprise significant number (prefix + extension) |
| `tollFreeNumber` | boolean | Whether the number is toll-free |
| `firstName` | string | Caller ID first name (deprecated) |
| `lastName` | string | Caller ID last name (deprecated) |
| `enabled` | boolean | Whether the voicemail group is active |
| `languageCode` | string | Language for audio announcements |
| `greeting` | enum | DEFAULT or CUSTOM |
| `greetingUploaded` | boolean | Whether a custom greeting WAV exists |
| `greetingDescription` | string | Custom greeting filename |
| `messageStorage` | object | INTERNAL or EXTERNAL (with externalEmail) |
| `notifications` | object | Email/SMS notification config |
| `faxMessage` | object | Fax receive settings |
| `transferToNumber` | object | Transfer-on-zero settings |
| `emailCopyOfMessage` | object | Email copy settings |
| `voiceMessageForwardingEnabled` | boolean | Voice message forwarding |
| `directLineCallerIdName` | object | Caller ID name settings |
| `dialByName` | string | Directory dial-by-name string |

### Key Observations

1. Voicemail groups are **location-scoped** -- they are created under a specific location.
   The mapper must resolve which location each group belongs to.

2. The `passcode` field is write-only (required on create, not returned on GET). The
   migration must generate a passcode -- CUCM voicemail PINs cannot be extracted from
   Unity Connection.

3. Custom greeting audio files cannot be migrated programmatically. The API has an upload
   endpoint for greetings, but the audio must be extracted from Unity Connection separately.

4. The `extension` field must be unique within the location. If the CUCM shared mailbox
   extension conflicts with a migrated user's extension, a decision is needed.

---

## Pipeline Integration

This feature requires changes across multiple pipeline phases.

### Phase 1: Discovery Enhancement

**File:** `src/wxcli/migration/cucm/unity_connection.py`

Add a new extractor method to query Unity Connection for shared call handlers (group
voicemail). The existing `extract_user_vm_settings()` method queries per-user VM settings;
a new `extract_shared_mailboxes()` method queries `/vmrest/handlers/callhandlers`.

```python
def extract_shared_mailboxes(self) -> list[dict]:
    """Extract Unity Connection shared/group voicemail handlers."""
    # GET /vmrest/handlers/callhandlers
    # Filter: IsPrimary=false (non-primary handlers are group mailboxes)
    # Return: DisplayName, Extension, ObjectId, DtmfAccessId
```

**Wire into discovery pipeline:** Add to the `discover` command alongside the existing
Unity Connection extraction. Store results under a new raw_data key: `"voicemail_groups"`.

### Phase 2: Normalizer

**File:** `src/wxcli/migration/transform/normalizers.py`

Add `normalize_voicemail_group()`:

```python
def normalize_voicemail_group(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a Unity Connection shared mailbox into a MigrationObject.

    (voicemail group pipeline: discovery -> normalize -> map -> plan -> execute)
    """
    name = raw.get("DisplayName") or raw.get("display_name") or "Unknown VM Group"
    extension = raw.get("Extension") or raw.get("DtmfAccessId")
    return MigrationObject(
        canonical_id=f"voicemail_group:{name}",
        provenance=Provenance(source_system="unity_connection"),
        pre_migration_state={
            "name": name,
            "extension": extension,
            "object_id": raw.get("ObjectId"),
            "notification_email": raw.get("notification_email"),
            "transfer_destination": raw.get("transfer_destination"),
            "greeting_type": raw.get("greeting_type", "DEFAULT"),
            # ... full field extraction
        },
    )
```

Add to `NORMALIZER_REGISTRY` and `RAW_DATA_MAPPING`:
```python
NORMALIZER_REGISTRY["voicemail_group"] = normalize_voicemail_group
RAW_DATA_MAPPING.append(("voicemail_groups", "voicemail_groups", "voicemail_group"))
```

### Phase 3: Cross-References

**File:** `src/wxcli/migration/transform/cross_reference.py`

Add cross-refs linking voicemail groups to their referencing features:

- `hunt_group_uses_voicemail_group` -- hunt pilot overflow → voicemail group
- `voicemail_group_in_location` -- voicemail group → location

### Phase 4: Canonical Model

**File:** `src/wxcli/migration/models.py`

Add `CanonicalVoicemailGroup`:

```python
class CanonicalVoicemailGroup(MigrationObject):
    """Unity Connection shared mailbox -> Webex Voicemail Group.
    (voicemail group migration pipeline)
    """
    name: str | None = None
    extension: str | None = None
    phone_number: str | None = None
    location_id: str | None = None
    language_code: str = "en_us"
    enabled: bool = True
    # Settings
    message_storage: dict[str, Any] = Field(default_factory=lambda: {"storageType": "INTERNAL"})
    notifications: dict[str, Any] = Field(default_factory=lambda: {"enabled": False})
    fax_message: dict[str, Any] = Field(default_factory=lambda: {"enabled": False})
    transfer_to_number: dict[str, Any] = Field(default_factory=lambda: {"enabled": False})
    email_copy_of_message: dict[str, Any] = Field(default_factory=lambda: {"enabled": False})
    caller_id_name: str | None = None
    # CUCM metadata
    cucm_object_id: str | None = None
    referring_features: list[str] = Field(default_factory=list)  # hunt group/CQ canonical_ids
```

### Phase 5: Mapper

**File:** `src/wxcli/migration/transform/mappers/voicemail_group_mapper.py` (new)

```python
class VoicemailGroupMapper(Mapper):
    """Maps Unity Connection shared mailboxes to Webex Voicemail Groups."""

    name = "voicemail_group_mapper"
    depends_on = ["location_mapper", "feature_mapper"]
```

**Mapping logic:**

1. Read normalized `voicemail_group` objects from store.
2. Resolve location via the hunt group/call queue that references the VM group
   (hunt group's location_id flows through to the voicemail group).
3. Map Unity Connection fields to Webex voicemail group fields.
4. Generate decisions for:
   - **Extension conflicts** -- voicemail group extension conflicts with user extensions
   - **Custom greeting loss** -- audio cannot be programmatically migrated
   - **Passcode generation** -- CUCM PINs cannot be extracted; generate or flag

### Phase 6: Execute Handler

**File:** `src/wxcli/migration/execute/handlers.py`

Add `handle_voicemail_group_create()`:

```python
def handle_voicemail_group_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    location_wid = None
    for cid, wid in deps.items():
        if cid.startswith("location:") and wid:
            location_wid = wid
            break
    if not location_wid:
        return []

    body = {
        "name": data.get("name"),
        "extension": data.get("extension"),
        "passcode": data.get("passcode", "0000"),  # Default; must be changed
        "languageCode": data.get("language_code", "en_us"),
        "messageStorage": data.get("message_storage", {"storageType": "INTERNAL"}),
        "notifications": data.get("notifications", {"enabled": False}),
        "faxMessage": data.get("fax_message", {"enabled": False}),
        "transferToNumber": data.get("transfer_to_number", {"enabled": False}),
        "emailCopyOfMessage": data.get("email_copy_of_message", {"enabled": False}),
    }
    if data.get("phone_number"):
        body["phoneNumber"] = data["phone_number"]
    if data.get("caller_id_name"):
        body["directLineCallerIdName"] = {
            "selection": "CUSTOM_NAME",
            "customName": data["caller_id_name"],
        }
        body["dialByName"] = data["caller_id_name"]

    url = _url(f"/telephony/config/locations/{location_wid}/voicemailGroups", ctx)
    return [("POST", url, body)]
```

Register in `HANDLER_REGISTRY`:
```python
("voicemail_group", "create"): handle_voicemail_group_create,
```

### Phase 7: Planner

**File:** `src/wxcli/migration/execute/planner.py`

Add `_expand_voicemail_group()`:

```python
def _expand_voicemail_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Voicemail group -> 1 op: create (tier 4, after features)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = obj.get("location_id")
    batch = loc_id if loc_id else None

    deps = []
    if loc_id:
        deps.append(_node_id(loc_id, "create"))
    # Depend on referring features (hunt groups, call queues) being created
    for feat_cid in obj.get("referring_features", []):
        deps.append(_node_id(feat_cid, "create"))

    return [_op(cid, "create", "voicemail_group",
                f"Create voicemail group {name}",
                depends_on=deps, batch=batch)]
```

Register in the expand dispatch table.

### Phase 8: Link Hunt Groups/Call Queues to VM Groups

After voicemail groups are created, hunt groups and call queues that overflow to voicemail
need to be configured with the voicemail group's extension or ID as their overflow
destination. This requires a second operation on the feature (e.g., `hunt_group:configure`)
that depends on the voicemail group being created first.

This is the most architecturally complex part -- it creates a dependency cycle concern:
features depend on locations, voicemail groups depend on features (for location resolution),
and features need voicemail groups for overflow config. Resolution: voicemail group creation
depends on features for location data, then a separate `configure_overflow` op on the
feature depends on the voicemail group being created.

---

## Decisions Generated

### New Decision Types

1. **VOICEMAIL_GROUP_PASSCODE** (Severity: LOW)
   - Unity Connection voicemail PINs cannot be extracted. A default passcode will be
     assigned. Admin must communicate new passcode to affected teams.
   - Options: Accept default passcode (0000), Manual override post-migration.

2. **VOICEMAIL_GROUP_GREETING_LOSS** (Severity: MEDIUM)
   - Custom greeting audio from Unity Connection cannot be programmatically migrated.
   - Options: Accept DEFAULT greeting, Manual upload post-migration.

3. **VOICEMAIL_GROUP_EXTENSION_CONFLICT** (Severity: HIGH)
   - Voicemail group extension conflicts with migrated user/workspace extension.
   - Options: Assign new extension, Reassign conflicting user's extension, Manual.

### Reused Decision Types

4. **MISSING_DATA** -- when Unity Connection shared mailbox data is incomplete or
   unavailable (e.g., Unity Connection API unreachable during discovery).

5. **FEATURE_APPROXIMATION** -- when Unity Connection features exceed Webex voicemail
   group capabilities (e.g., multiple greetings by time-of-day, caller input rules).

---

## Feature Gap Analysis: Unity Connection vs Webex Voicemail Groups

| UC Feature | Webex VM Group Support | Gap? |
|------------|----------------------|------|
| Shared mailbox with extension | Yes | No |
| Custom greeting (single) | Yes (upload WAV) | Audio not auto-migrated |
| Multiple greetings (time-of-day) | No -- single greeting only | Yes |
| Email notification on new message | Yes (destination field) | No |
| Email copy of message | Yes (emailCopyOfMessage) | No |
| Fax reception | Yes (faxMessage) | No |
| Transfer on zero | Yes (transferToNumber) | No |
| Message forwarding | Yes (voiceMessageForwardingEnabled) | No |
| Caller input rules (DTMF routing) | No | Yes -- major gap |
| Alternate extensions | No | Yes |
| Message expiry/retention | No | Yes |
| Dispatch messaging (round-robin) | No | Yes |
| Secure/private messages | No | Yes |
| VPIM networking (inter-system) | No | Yes |
| Per-member access permissions | Not configurable via API | Partial gap |

**Summary:** Core shared mailbox functionality (greeting, notifications, fax, transfer)
maps well. Advanced Unity Connection features (caller input rules, dispatch messaging,
alternate extensions) have no Webex equivalent.

---

## Documentation Updates Required

1. **`docs/reference/call-features-additional.md`** -- Add or expand Voicemail Groups
   section with full API reference (currently may be absent or minimal).

2. **`src/wxcli/migration/CLAUDE.md`** -- Update file map to include
   `voicemail_group_mapper.py`.

3. **`src/wxcli/migration/transform/mappers/CLAUDE.md`** -- Add VoicemailGroupMapper
   to mapper inventory (Tier 3, depends on location_mapper + feature_mapper).

4. **`docs/runbooks/cucm-migration/decision-guide.md`** -- Add entries for the three
   new decision types.

5. **`docs/knowledge-base/migration/kb-feature-mapping.md`** -- Add section on voicemail
   group mapping, including the feature gap table above.

6. **`docs/runbooks/cucm-migration/operator-runbook.md`** -- Add note about Unity
   Connection shared mailbox discovery prerequisites.

---

## Test Strategy

### Unit Tests

1. **Normalizer: normalize_voicemail_group**
   - Input: Unity Connection shared mailbox dict
   - Assert: correct canonical_id, extension, name in pre_migration_state

2. **Mapper: VoicemailGroupMapper basic mapping**
   - Fixture: 1 voicemail group normalized, 1 location, 1 hunt group referencing it
   - Assert: CanonicalVoicemailGroup produced with correct location_id and fields

3. **Mapper: extension conflict detection**
   - Fixture: voicemail group extension 5896 + user with same extension 5896
   - Assert: VOICEMAIL_GROUP_EXTENSION_CONFLICT decision generated

4. **Mapper: custom greeting loss detection**
   - Fixture: voicemail group with greeting_type=CUSTOM
   - Assert: VOICEMAIL_GROUP_GREETING_LOSS decision generated

5. **Mapper: passcode decision**
   - Fixture: any voicemail group
   - Assert: VOICEMAIL_GROUP_PASSCODE decision generated (always, since PINs not extractable)

6. **Handler: handle_voicemail_group_create**
   - Input: data dict with all required fields, deps with location Webex ID
   - Assert: POST to `/telephony/config/locations/{id}/voicemailGroups` with correct body

7. **Handler: missing location**
   - Input: data dict, empty deps
   - Assert: returns empty list

8. **Planner: _expand_voicemail_group**
   - Input: CanonicalVoicemailGroup with location_id and referring_features
   - Assert: 1 op with correct dependencies on location and feature creates

### Integration Tests

9. **Full pipeline: hunt group with VM overflow**
   - Fixture: hunt pilot with voiceMailUsage=USE_PILOT_NUMBER, Unity Connection
     shared mailbox, matching location
   - Assert: plan contains voicemail_group:create op after hunt_group:create

10. **Feature gap detection**
    - Fixture: Unity Connection mailbox with callerInputRules set
    - Assert: FEATURE_APPROXIMATION decision with correct gap description

---

## Implementation Phases

This feature spans multiple pipeline phases and should be implemented incrementally:

### Phase A: Detection + Report (Low risk, high value)
- Add detection of voiceMailUsage != NONE in feature_mapper
- Generate MISSING_DATA decision flagging the gap in the assessment report
- No new normalizer, mapper, or handler needed
- **Immediate value:** the assessment report now surfaces the gap

### Phase B: Full Pipeline (Higher risk)
- Add Unity Connection shared mailbox extractor
- Add normalizer, cross-refs, canonical model
- Add mapper, handler, planner
- Add all unit tests

### Phase C: Overflow Linkage
- Wire hunt group/call queue overflow to voicemail group
- Handle dependency ordering
- Integration tests

**Recommendation:** Start with Phase A. It requires ~20 lines of code in the feature
mapper and immediately surfaces the problem in assessment reports. Phase B and C can
follow when there is a real migration engagement with shared mailboxes.

---

## Implementation Checklist

### Phase A (Detection)
- [ ] Enhance FeatureMapper to generate MISSING_DATA decision when voiceMailUsage != NONE
- [ ] Add 1 unit test for the new decision
- [ ] Verify the decision appears in assessment reports

### Phase B (Full Pipeline)
- [ ] Add `extract_shared_mailboxes()` to `unity_connection.py`
- [ ] Add `normalize_voicemail_group()` to `normalizers.py`
- [ ] Add `CanonicalVoicemailGroup` to `models.py`
- [ ] Add `DecisionType.VOICEMAIL_GROUP_PASSCODE`
- [ ] Add `DecisionType.VOICEMAIL_GROUP_GREETING_LOSS`
- [ ] Add `DecisionType.VOICEMAIL_GROUP_EXTENSION_CONFLICT`
- [ ] Add `VoicemailGroupMapper` (new file)
- [ ] Add cross-refs to `cross_reference.py`
- [ ] Add `handle_voicemail_group_create` to `handlers.py`
- [ ] Add `_expand_voicemail_group` to `planner.py`
- [ ] Write 8 unit tests
- [ ] Update CLAUDE.md files (migration, mappers)
- [ ] Update runbook and knowledge base docs

### Phase C (Overflow Linkage)
- [ ] Add `hunt_group:configure_overflow` operation
- [ ] Wire dependency graph (voicemail_group:create -> feature:configure_overflow)
- [ ] Write 2 integration tests
