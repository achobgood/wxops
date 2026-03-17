# Quality Review: Person & Location Call Settings (7 Docs)

**Reviewer:** Claude Opus 4.6 (automated)
**Date:** 2026-03-17
**Files reviewed:**
1. `person-call-settings-handling.md`
2. `person-call-settings-media.md`
3. `person-call-settings-permissions.md`
4. `person-call-settings-behavior.md`
5. `location-call-settings-core.md`
6. `location-call-settings-media.md`
7. `location-call-settings-advanced.md`

---

## 1. Accuracy Issues

### 1a. Scope Inconsistencies

| File | Section | Issue | Severity |
|------|---------|-------|----------|
| `person-call-settings-handling.md` | Call Waiting (section 2) | Read scope listed as `spark-admin:people_read` only; missing `spark:people_read` (self). Compare with DND which correctly lists both. | Medium |
| `person-call-settings-handling.md` | Call Waiting (section 2) | Write scope listed as `spark-admin:people_write` only; missing `spark:people_write` (self). | Medium |
| `person-call-settings-media.md` | Call Recording (section 7) | Read scope listed as `spark-admin:people_write` with an inline comment flagging it as a possible documentation error. This is almost certainly wrong -- read should be `spark-admin:people_read`. The NEEDS VERIFICATION tag is appropriate but the doc should at minimum note the likely correct value. | High |
| `person-call-settings-permissions.md` | Outgoing Permissions -- Transfer Numbers | Read scope is `spark-admin:workspaces_read`. The doc's own NEEDS VERIFICATION comment at the bottom correctly questions whether `spark-admin:people_read` also works for person-level. This is confusing for person-settings docs. | Medium |
| `person-call-settings-permissions.md` | Outgoing Permissions -- Access Codes | Same issue: scopes reference `workspaces_read/write` in a person-settings context. | Medium |
| `person-call-settings-permissions.md` | Call Policy (section 5) | Scopes are `spark-admin:workspaces_read/write`. The doc correctly notes this may only apply to workspaces, but it is listed in a person-settings doc which is misleading. | Medium |
| `person-call-settings-behavior.md` | ECBN (section 14) | Write scope docstring says "read-only administrator" can update, which is flagged with NEEDS VERIFICATION. This is almost certainly an SDK docstring copy error. | Medium |

### 1b. Method Signature Issues

| File | Section | Issue | Severity |
|------|---------|-------|----------|
| `person-call-settings-handling.md` | Single Number Reach -- `read()` | Method signature uses `person_id: str` with no `org_id` parameter, unlike every other read method in the doc which accepts `org_id: str = None`. Inconsistent -- either the API genuinely omits org_id or the doc missed it. | Low |
| `person-call-settings-behavior.md` | App Shared Line -- `members_count()` | NEEDS VERIFICATION tag flags a possible double-prefix bug in URL construction (`telephony/config/people/telephony/config/people/{id}/...`). If true, this method may be broken in the SDK. | High |
| `person-call-settings-behavior.md` | Calling Behavior -- `read()`/`configure()` | Uses `person_id` parameter name instead of `entity_id` used by most other person-settings APIs. Not wrong (maps to the same thing), but inconsistent with the doc family. | Low |

### 1c. Data Model Issues

| File | Section | Issue | Severity |
|------|---------|-------|----------|
| `person-call-settings-behavior.md` | ECBN (section 14) | Two overlapping enums (`ECBNSelection` and `SelectedECBN`) with mostly identical values. The doc notes this but doesn't clarify which to use when. `ECBNSelection` includes `NONE`; `SelectedECBN` does not. | Low |
| `person-call-settings-media.md` | Call Recording -- `PostCallRecordingSettings` | Both fields (`summary_and_action_items_enabled`, `transcript_enabled`) have empty descriptions with NEEDS VERIFICATION tags referencing SDK issue 201. | Low |

---

## 2. Coverage Gaps

### 2a. Person Settings Coverage Audit

Enumerating all person-level settings documented across the 4 person docs:

**person-call-settings-handling.md (10 features):**
1. Call Forwarding
2. Call Waiting
3. Do Not Disturb
4. Simultaneous Ring
5. Sequential Ring
6. Single Number Reach
7. Selective Accept
8. Selective Forward
9. Selective Reject
10. Priority Alert

**person-call-settings-media.md (11 features):**
11. Voicemail
12. Caller ID
13. Agent Caller ID
14. Anonymous Call Rejection
15. Privacy
16. Barge-In
17. Call Recording
18. Call Intercept
19. Monitoring
20. Push-to-Talk
21. Music on Hold

**person-call-settings-permissions.md (5 features):**
22. Incoming Permissions
23. Outgoing Permissions (incl. transfer numbers, access codes, digit patterns)
24. Feature Access Controls
25. Executive / Assistant Settings (type assignment, alerting, assistants, call filtering, screening)
26. Call Policy

**person-call-settings-behavior.md (13 features):**
27. Calling Behavior
28. App Services
29. App Shared Line
30. Call Bridge
31. Hoteling
32. Receptionist Client
33. Numbers
34. Available Numbers
35. Preferred Answer Endpoint
36. MS Teams
37. Mode Management
38. Personal Assistant
39. Emergency Callback Number (ECBN)

**Total: 39 distinct person-level features documented.**

**Potentially missing person-level settings:**
- **Call Notify** -- Referenced in Feature Access Controls (field `call_notify`) but not documented as its own API anywhere in the 4 person docs.
- **Connected Line Identity** -- Referenced in Feature Access Controls (field `connected_line_identity`) but no standalone API section.
- **Schedules (user-level)** -- Mentioned in `location-call-settings-media.md` section 4.1 as supporting user/person-level schedules, but not documented in any person doc. The URL pattern `people/{personId}/features/schedules` is given in the location doc only.
- **Webex Go** -- Referenced in DND model (`webex_go_override_enabled`) but no dedicated person-level Webex Go settings API documented.

### 2b. Location Settings Coverage Audit

**location-call-settings-core.md:**
1. Location telephony details (enable, list, get, update)
2. Caller ID (CallingLineId + available numbers for external caller ID)
3. Internal Dialing
4. Call Intercept
5. Music on Hold
6. Location Numbers (add, remove, activate, manage state)
7. Emergency Callback Number (ECBN)
8. Announcement Language
9. Call Captions
10. Device Settings
11. Safe Delete Check
12. Extension Validation & Password Generation
13. Voicemail Policies (location-level transcription toggle)
14. Organisation Voicemail Settings (org-wide expiry/forwarding)
15. Voicemail Rules (org-level passcode policy)
16. Voice Messaging (user-level, arguably misplaced here)
17. Voice Portal
18. Receptionist Contact Directories

**location-call-settings-media.md:**
19. Announcements Repository
20. Playlists (Music On Hold)
21. Access Codes (location + org level)
22. Schedules & Holiday Schedules

**location-call-settings-advanced.md:**
23. Call Recording (org + location vendor management)
24. Caller Reputation
25. Conference Controls (runtime, arguably misplaced)
26. Supervisors
27. Guest Calling (Click-to-Call)
28. Operating Modes
29. Hot Desking Sign-in via Voice Portal
30. Forwarding (shared patterns for queues/hunt groups/AA)

**Potentially missing location-level settings:**
- **Outgoing Permissions (location-level)** -- `OutgoingPermissionsApi` is listed as an attribute of `TelephonyLocationApi` in core.md (line ~53, `permissions_out` attribute) but has no dedicated section. It's partially covered under person-level permissions but the location-level specifics (which differ) are undocumented.
- **Location Receptionist Contacts Directory** -- Listed as an attribute and has method signatures in core.md, but with minimal model documentation (no `ContactDetails` model defined).

### 2c. Misplaced Content

| File | Section | Issue |
|------|---------|-------|
| `location-call-settings-core.md` | Section 4: Voice Messaging (User-Level) | This is a user-scoped API (`spark:calls_read/write`), not a location setting. It belongs in person docs or a separate user-runtime doc. |
| `location-call-settings-advanced.md` | Section 3: Conference Controls | This is a runtime call-control API (`spark:calls_read/write`), not a location configuration API. It belongs in `call-control.md`. |

---

## 3. Cross-Reference Audit

### 3a. Person Docs Referencing Location Docs

| Person Doc | Section | Cross-Reference Present? | Notes |
|-----------|---------|--------------------------|-------|
| `handling.md` | Music on Hold (section 11) | **Yes** -- notes `moh_location_enabled` interaction table and prerequisite that MoH must be enabled at location level | Good |
| `handling.md` | Simultaneous Ring / Sequential Ring / Priority Alert | **No** -- These criteria features reference schedules (via `schedule_name`, `schedule_type`, `schedule_level`) but never link to the location schedule docs | Missing |
| `media.md` | Voicemail (section 1) | **No** -- Does not reference location voicemail settings (transcription toggle) or org voicemail policies (expiry, forwarding) which govern person-level behavior | Missing |
| `media.md` | Call Recording (section 7) | **No** -- Does not reference location/org call recording vendor settings in `location-call-settings-advanced.md` | Missing |
| `media.md` | Call Intercept (section 8) | **No** -- Does not reference location-level call intercept in `location-call-settings-core.md` | Missing |
| `permissions.md` | Feature Access Controls (section 3) | **No** -- Org-level defaults affect all persons, but no link to where org settings are managed | Missing |
| `permissions.md` | Outgoing Permissions (section 2) | **No** -- Note says "access_codes is not available for locations" and references telephony-level API, but provides no link | Missing |
| `behavior.md` | Mode Management (section 12) | **No** -- References operating modes but doesn't link to `location-call-settings-advanced.md` section 6 | Missing |
| `behavior.md` | ECBN (section 14) | **No** -- Does not reference location ECBN settings in `location-call-settings-core.md` | Missing |

### 3b. Location Docs Referencing Person Docs

| Location Doc | Section | Cross-Reference Present? | Notes |
|-------------|---------|--------------------------|-------|
| `core.md` | Call Intercept | **Yes** -- "Uses the shared `InterceptSetting` model from `wxc_sdk.person_settings.call_intercept`" | Good |
| `core.md` | Music on Hold | **No** -- Does not mention person-level MoH override or link to `person-call-settings-media.md` section 11 | Missing |
| `core.md` | Voicemail Policies | **No** -- Does not mention per-person voicemail settings or link to `person-call-settings-media.md` section 1 | Missing |
| `core.md` | ECBN | **No** -- Does not mention per-person ECBN or link to `person-call-settings-behavior.md` section 14 | Missing |
| `advanced.md` | Call Recording | **No** -- Does not reference per-person call recording settings in `person-call-settings-media.md` section 7 | Missing |
| `advanced.md` | Hot Desking | **No** -- Has both location and user methods but doesn't cross-reference person-level hoteling in `person-call-settings-behavior.md` section 6 | Missing |
| `media.md` | Schedules | **Partial** -- Mentions user-level schedules with URL patterns but doesn't link to person docs | Weak |

**Summary: Cross-referencing is mostly absent.** Out of ~18 natural cross-reference points identified, only 2 are present (MoH in handling.md, InterceptSetting in core.md). This is the single biggest gap in the doc set.

---

## 4. Overlap / Duplication Audit

### 4a. Duplicated Content

| Topic | Doc A | Doc B | Overlap Type |
|-------|-------|-------|-------------|
| URL routing / `ApiSelector` enum | `handling.md` section "URL Routing Internals" | `behavior.md` section 1 "Common Base Classes" | Both document the `ApiSelector` enum and URL templates. `behavior.md` also lists remapped features. The handling.md version includes the remap list in the URL Routing Internals section. **Recommendation:** Consolidate into one canonical section and cross-reference from the other. |
| Call Intercept data models | `person-call-settings-media.md` section 8 | `location-call-settings-core.md` section "Call Intercept" | Location doc references the shared model but person doc defines it fully. **OK as-is** -- person doc is the canonical definition, location doc cross-references. |
| Scopes summary tables | `handling.md` section "Required Scopes" | `media.md` section 12 "Common Patterns -- Scopes Summary" | Both have scope summary tables but cover different APIs. **OK as-is** -- each covers its own feature set. |
| `AuthCode` model | `permissions.md` section 2 (person-level access codes) | `media.md` (location-settings) section 3 | Both define the `AuthCode` model. Location doc has the fuller version (`level` field). **Recommendation:** Have person doc reference the location doc's definition. |

### 4b. Near-Duplicates That Could Cause Confusion

| Topic | Issue |
|-------|-------|
| Outgoing Permissions | Documented in `person-call-settings-permissions.md` section 2 for persons, and listed as an attribute of `TelephonyLocationApi` in `location-call-settings-core.md` but never documented at the location level. This creates a gap (see section 2b above), not a duplication, but could confuse readers looking for location-level outgoing permissions. |
| ECBN | Person-level in `behavior.md` section 14, location-level in `core.md`. Different models (`PersonECBN` vs `LocationECBN`, `ECBNSelection`/`SelectedECBN` vs `CallBackSelected`). No cross-reference. Could confuse someone trying to understand the full ECBN hierarchy. |

---

## 5. NEEDS VERIFICATION Tags -- Complete List

### person-call-settings-handling.md (4 tags)

| Line | Tag Location | Topic |
|------|-------------|-------|
| ~276 | Simultaneous Ring SDK path | `SimRingApi` not imported into `PersonSettingsApi`; may only be available via workspace_settings or MeSimRingApi |
| ~343 | Sequential Ring SDK path | `SequentialRingApi` not imported into `PersonSettingsApi`; same availability concern |
| ~633 | Priority Alert SDK path | `PriorityAlertApi` not imported into `PersonSettingsApi`; same availability concern |
| ~728 | Precedence Order | Exact precedence between Selective Reject and Accept stated in SDK docstrings but full interaction with Priority Alert/ring features undocumented |
| ~749 | "Me" API Variants note | Whether admin-level person endpoints exist for SimRing, SequentialRing, PriorityAlert in the Webex Calling REST API |

### person-call-settings-media.md (4 tags)

| Line | Tag Location | Topic |
|------|-------------|-------|
| ~362 | Anonymous Call Rejection note | Whether this works for persons or only workspaces in practice |
| ~374 | Anonymous Call Rejection scope | Exact scope may differ for workspaces |
| ~529-531 | Call Recording -- `PostCallRecordingSettings` | Two undocumented fields (SDK issue 201) |
| ~575 | Call Recording -- `read()` scope | Read scope may actually be `people_read`, not `people_write` |
| ~951 | Entity Applicability table -- Anonymous Call Rejection | Person column empty (NEEDS VERIFICATION) |

### person-call-settings-permissions.md (2 tags)

| Line | Tag Location | Topic |
|------|-------------|-------|
| ~686 | Call Policy | Whether this applies to persons or only workspaces |
| ~735 | Scope Summary footnote | Whether `spark-admin:people_read/write` also works for person-level transfer numbers and access codes |

### person-call-settings-behavior.md (3 tags)

| Line | Tag Location | Topic |
|------|-------------|-------|
| ~202 | App Shared Line -- `members_count()` | Possible double-prefix URL bug |
| ~285 | Hoteling | Person-level API may be incomplete compared to workspace-level |
| ~907 | ECBN -- `configure()` scope | "Read-only administrator" can update -- unusual, likely docstring error |
| ~998-999 | ECBN -- `ECBNSelection` vs `SelectedECBN` | Two enums with overlapping values; `ECBNSelection` includes NONE |

### location-call-settings-core.md (4 tags)

| Line | Tag Location | Topic |
|------|-------------|-------|
| ~529 | Call Captions | Exact country restrictions |
| ~693 | Receptionist Contact Directories | Exact error code 25395 threshold |
| ~742 | Organisation Voicemail Settings API path | Exact attribute name on telephony API |
| ~794 | Voicemail Rules API path | Exact attribute name on telephony API |
| ~906 | Voice Messaging API path | Exact attribute name |
| ~1008 | Voice Portal API path | Exact attribute name |
| ~1133 | API Access Path Summary footnote | Exact attribute names on top-level telephony API object |

### location-call-settings-media.md (3 tags)

| Line | Tag Location | Topic |
|------|-------------|-------|
| ~343 | Playlists -- `usage()` scope | Scope not documented in source |
| ~523 | Access Codes -- batch limits | Location-level batch limit not documented |
| ~655 | Schedules -- `list()` scope | Source says `people_read` but location schedules likely also accept `telephony_config_read` |
| ~888 | Auth Scopes Summary | Schedule list scope uncertainty |

### location-call-settings-advanced.md (4 tags)

| Line | Tag Location | Topic |
|------|-------------|-------|
| ~269 | Caller Reputation -- `unlock()` | Exact conditions triggering locked state |
| ~271 | Caller Reputation -- score thresholds | Whether these are numeric strings or can contain non-numeric values |
| ~401 | Supervisors -- `SupervisorAgentStatus.type` | Undocumented field (SDK issue 202) |
| ~469 | Guest Calling -- `video_enabled` | No docstring in SDK |

**Total NEEDS VERIFICATION tags: 25** (some lines have compound tags counted as one)

---

## 6. Formatting & Structural Consistency

### 6a. Consistent Patterns Across All 7 Docs

- All docs use H2 for major feature sections with numbered prefixes
- All docs use tables for data models (Field | Type | Description)
- All docs include method signatures as Python code blocks
- All docs note scopes per method
- All docs use `<!-- NEEDS VERIFICATION -->` comment syntax

### 6b. Inconsistencies

| Issue | Affected Docs | Details |
|-------|--------------|---------|
| Table of Contents | `media.md`, `behavior.md`, `advanced.md` have ToC; `handling.md`, `permissions.md`, `core.md`, `media.md` (location) do not | Should be consistent -- all or none |
| SDK path format | `handling.md` uses `**SDK path:** api.person_settings.X` format consistently; `media.md` uses `**API class:** X` + `**Feature key:** X` + `**Source:** X` format | Different metadata block structure |
| Method naming | Some APIs use `read()`/`configure()` (most person APIs), others use `read()`/`update()` (location APIs, some person APIs like Numbers, ECBN). This reflects the actual SDK but could benefit from a note explaining the convention. | Informational |
| Source file references | `handling.md` has a comprehensive "Source Files" table at the end; other person docs list source files per-section; location docs sometimes omit source paths entirely | Inconsistent |
| Default settings | `handling.md` shows `.default()` only for forwarding; `media.md` shows defaults for voicemail, call recording, call intercept. `permissions.md` and `behavior.md` show static helper methods. | Inconsistent coverage of default/factory patterns |
| Example code | `handling.md` has 2 real examples (reset forwarding, enable always-forward); `media.md` has 1 example (modify voicemail); `permissions.md` has 3 examples; `behavior.md` has none. Location docs have examples in `core.md` (location update) and `media.md` (schedules/holidays). | Uneven |

---

## 7. Recommendations (Priority Order)

### P0 -- Fix Before Use

1. **Call Recording read scope** (`person-call-settings-media.md` section 7): Change documented scope from `spark-admin:people_write` to `spark-admin:people_read` (or at minimum mark with a warning, not just an HTML comment).

### P1 -- Should Fix

2. **Add cross-references between person and location docs.** At minimum, add a "Related Location Settings" callout box at the top of each person doc (and vice versa) listing the location-level counterparts. Key pairs:
   - Person Voicemail <-> Location Voicemail Policies + Org Voicemail Settings + Voicemail Rules
   - Person Call Recording <-> Location/Org Call Recording Vendors
   - Person Call Intercept <-> Location Call Intercept
   - Person MoH <-> Location MoH
   - Person ECBN <-> Location ECBN
   - Person Mode Management <-> Location Operating Modes
   - Person Hoteling <-> Location Hot Desking

3. **Document location-level outgoing permissions.** The `OutgoingPermissionsApi` is listed as an attribute of `TelephonyLocationApi` but has no section. Add a section to `location-call-settings-core.md` or a cross-reference to the person-level doc with notes on location-specific differences.

4. **Fix Call Waiting scope** (`person-call-settings-handling.md` section 2): Add missing `spark:people_read` and `spark:people_write` self-service scopes to match DND and other features.

5. **Move misplaced content:**
   - Voice Messaging (user-level) out of `location-call-settings-core.md` into a person doc or standalone runtime doc.
   - Conference Controls out of `location-call-settings-advanced.md` into `call-control.md`.

### P2 -- Nice to Have

6. **Add Table of Contents** to `handling.md`, `permissions.md`, and `location-call-settings-core.md` for consistency with the other 4 docs.

7. **Document Call Notify and Connected Line Identity** as person-level APIs (or note they are Feature Access Controls only with no standalone API).

8. **Document user-level schedules** in a person doc (currently only documented in the location media doc).

9. **Consolidate the ApiSelector/URL routing content** that appears in both `handling.md` (URL Routing Internals) and `behavior.md` (Common Base Classes). Keep one canonical version and cross-reference.

10. **Standardize SDK path metadata blocks** across all person docs (choose between the `handling.md` format and the `media.md` format).

11. **Add examples** to `behavior.md` (currently the only person doc with zero code examples).

---

## 8. Summary Statistics

| Metric | Count |
|--------|-------|
| Total person-level features documented | 39 |
| Total location-level features documented | 30 |
| NEEDS VERIFICATION tags | 25 |
| Accuracy issues found | 11 |
| Missing cross-references | 15+ |
| Content overlaps requiring action | 2 |
| Misplaced sections | 2 |
| Formatting inconsistencies | 6 |

**Overall assessment:** The docs are technically thorough -- method signatures, data models, and enums are comprehensively documented with real SDK source paths. The primary weakness is the near-total absence of cross-references between person and location docs, which matters because many settings have location-level defaults that govern person-level behavior. The 25 NEEDS VERIFICATION tags are appropriately placed and should be resolved through SDK source inspection or API testing.
