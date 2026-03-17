# Quality Review: Call Features & Call Routing Reference Docs

**Reviewer**: Claude (automated quality review)
**Date**: 2026-03-17
**Files reviewed**:
1. `call-features-major.md` (AA, CQ, HG)
2. `call-features-additional.md` (Paging, Call Park, Call Pickup, VM Groups, CX Essentials)
3. `call-routing.md` (Dial Plans, Trunks, Route Groups, Route Lists, Translation Patterns, PSTN, PNC)

---

## 1. call-features-major.md

### 1.1 Accuracy

**Method signatures** -- All signatures include proper type hints, defaults, and return types. Verified patterns: `list()` returns `Generator`, `create()` returns `str`, `update()` returns `None`, `delete_*()` returns `None`. Consistent across AA, CQ, and HG.

**Scopes** -- Section 6 lists `spark-admin:telephony_config_read` (read) and `spark-admin:telephony_config_write` (write). This is correct for all telephony config endpoints.

**Data models** -- Thorough coverage:
- `AutoAttendant`: 14 fields documented with required-for-create column.
- `CallQueue` (extends `HGandCQ`): 14 fields.
- `HuntGroup` (extends `HGandCQ`): 10 fields.
- `HGandCQ` base: 17 fields in Section 5.
- All relevant enums documented (`AutoAttendantAction`, `Policy`, `CQRoutingType`, `OverflowAction`, `CallParkRecall`, etc.).

**One concern**: The `Policy` enum table (line 198) says `WEIGHTED` has max 100 agents. The Feature Comparison appendix (line 722) says "100-1,000" for "other policies" on both CQ and HG. These should be reconciled -- WEIGHTED is specifically capped at 100 in the API docs, so the appendix line "100-1,000" is misleading because it lumps WEIGHTED with CIRCULAR/REGULAR/UNIFORM (which are 1,000). Consider splitting the row: "Max agents (WEIGHTED)" = 100, "Max agents (CIRCULAR/REGULAR/UNIFORM)" = 1,000.

### 1.2 Gaps

**AA menus**: Fully covered. `AutoAttendantMenu`, `AutoAttendantKeyConfiguration`, `AutoAttendantAction` enum (10 actions), `CallTreatment` (no-input handling), `ActionToBePerformedAction` (post-retry actions) -- all present.

**CQ routing policies**: All five `Policy` values documented (CIRCULAR, REGULAR, SIMULTANEOUS, UNIFORM, WEIGHTED) with max agent counts. `CQRoutingType` (PRIORITY_BASED, SKILL_BASED) documented.

**CQ overflow**: `OverflowSetting` and `OverflowAction` enum fully covered. `QueueSettings` covers queue_size, overflow, welcome/wait/comfort messages, MOH, whisper.

**HG ring patterns**: `HGCallPolicies` covers `Policy`, `waiting_enabled`, `group_busy_enabled`, `no_answer`, `busy_redirect`, `business_continuity_redirect`. `NoAnswer` model has all fields including `next_agent_enabled`, `next_agent_rings`, `forward_enabled`, `destination`, `number_of_rings`.

**CQ policy sub-API**: Holiday service, night service, stranded calls, forced forward -- all four covered with their data models.

**Missing items**:
- **CQ callback feature**: `WaitMessageSetting` includes `callback_option_enabled` and `minimum_estimated_callback_time`, but there is no narrative explanation of how the callback feature works end-to-end (caller receives callback instead of waiting). This is a significant CX feature that deserves a brief behavioral note.
- **CQ supervisor features**: The org-level `CallQueueSettings` references barge-in, silent monitoring, and supervisor coaching tones, but there is no mention of the supervisor APIs themselves (if they exist in the SDK). At minimum, note that supervisor actions are performed via the Call Control API (cross-reference needed).
- **HG `waiting_enabled` behavioral nuance**: The doc says "If false, acts as 'advance when busy'" (line 504). This is correct but could be more explicit: when `waiting_enabled=False`, agents already on a call are skipped in the ring sequence; when `True`, the call waits (rings) even if the agent is on another call (call waiting).
- **Announcement file upload limitation**: Mentioned for both AA and CQ, but not for HG. The appendix correctly shows "No" for HG announcement file management, but no narrative mention exists.

### 1.3 Cross-References

**Present**:
- Section 4 (Shared Forwarding API) is referenced from AA (line 131), HG (line 551), and CQ (implicitly via the forwarding sub-API paths at line 559-562).
- Section 7 (Dependencies) references locations, schedules, and agent licensing.

**Missing**:
- **No cross-reference to `provisioning.md`** for creating locations or users. Section 7.1 says "Location must exist" and 7.4 says "Agents must be existing people" but doesn't point the reader to `provisioning.md`.
- **No cross-reference to `call-routing.md`**. AA/CQ/HG all have phone numbers that could be part of dial plans or route lists. When an AA transfers to an external number, that call traverses the call routing chain -- no mention of this.
- **No cross-reference to `call-features-additional.md`**. Call Park recall uses hunt groups (documented in call-features-additional.md), and voicemail groups can be used as overflow destinations for CQ/HG -- neither linkage is mentioned.
- **No cross-reference to `person-call-settings-handling.md`** for user-level call forwarding (which interacts with HG/CQ agent behavior).

### 1.4 NEEDS VERIFICATION Tags

| Line | Tag Content | Assessment |
|------|-------------|------------|
| 323 | `<!-- NEEDS VERIFICATION: check if this has been fixed in newer API versions -->` (Agent type always returning PEOPLE) | **Not resolvable from other docs.** Requires live API testing. Keep tag. |
| 711 | `<!-- NEEDS VERIFICATION -->` (HG holiday service: "No dedicated API") | **Partially resolvable.** The HG forwarding API (Section 4) supports selective forwarding rules based on holiday_schedule -- this IS the holiday service mechanism for HGs. The appendix entry is misleading. HGs don't have a dedicated "holiday service policy" like CQs, but they DO have schedule-based forwarding. Suggest changing "No dedicated API" to "Via forwarding rules (schedule-based)" and removing the tag. |
| 712 | `<!-- NEEDS VERIFICATION -->` (HG night service: "No dedicated API") | **Same as above.** HG forwarding supports business_schedule-based rules. Suggest same treatment. |

### 1.5 Formatting

- Consistent structure: Overview > SDK access path > API Operations table > Key Data Models > sub-sections.
- Every section starts with an Overview paragraph with "Use a [feature] when..." guidance.
- Convenience constructors shown for all three features.
- Feature Comparison appendix table is a strong addition.
- Minor inconsistency: AA uses a table for API operations (lines 31-38), CQ uses a table (lines 148-157), HG uses a table (lines 466-472) -- all consistent.
- Code examples provided for CQ agent management but not for AA menu configuration or HG agent management. Consider adding a brief AA menu config example.

---

## 2. call-features-additional.md

### 2.1 Accuracy

**Method signatures** -- All follow the same patterns as call-features-major.md. Return types, parameter types, and optional/required markers are present.

**Scopes** -- Section correctly identifies the split scopes for CX Essentials: `spark-admin:people_read`/`people_write` for queue recording vs `spark-admin:telephony_config_read`/`telephony_config_write` for wrap-up and screen pop.

**Data models** -- Thorough:
- `Paging`: 14 fields with required-for-create column.
- `CallPark`: 6 fields; `RecallHuntGroup` and `CallParkRecall` enum documented.
- `CallParkExtension`: Lightweight model (3 fields) -- correct.
- `CallPickup`: 6 fields; `PickupNotificationType` enum with 4 values.
- `VoicemailGroupDetail`: 18 fields with factory defaults documented.
- CX Essentials: `ScreenPopConfiguration`, `WrapUpReason`/`WrapUpReasonDetails`, `QueueWrapupReasonSettings` all present.

**One concern**: `CallRecordingSetting` (used by CX Essentials queue recording, line 1136) is listed in the shared models table but its fields are never documented anywhere in this file. The `read()` and `configure()` methods reference it, but the reader has no idea what fields it contains. This is a gap -- either document the model or cross-reference where it's documented.

### 2.2 Gaps

**All features covered**: Paging Groups, Call Park, Call Park Extensions, Call Pickup, Voicemail Groups, CX Essentials -- all present.

**Missing items**:
- **CallRecordingSetting model fields**: As noted above, not documented. Likely includes `enabled`, `recording_type` (always/never/on_demand), `pause_resume_enabled`, `vendor`, etc. This is a significant omission for anyone implementing queue recording.
- **Paging Group limits**: States "up to 75 targets" but doesn't mention any limit on originators.
- **Call Park available_agents return type**: Uses `PersonPlaceAgent` but this model's fields are only in the quick reference table (line 1130), not documented inline like other feature-specific models. A brief field table would help.
- **Voicemail Group sub-models**: `VoicemailMessageStorage`, `VoicemailNotifications`, `VoicemailFax`, `VoicemailTransferToNumber`, `VoicemailCopyOfMessage` are referenced in `VoicemailGroupDetail` as required fields (set by factory) but none of their fields are documented. These are non-trivial models (storage type, email addresses, notification settings) that someone customizing beyond factory defaults would need.

### 2.3 Cross-References

**Present**:
- Dependencies section (line 1179) correctly notes Call Park requires Call Park Extensions and optionally Hunt Groups.
- CX Essentials dependencies note that Call Queues must exist first.

**Missing**:
- **No cross-reference to `call-features-major.md`** for Call Queues (CX Essentials depends on them), Hunt Groups (Call Park recall depends on them), or Auto Attendants (Voicemail Groups can be assigned to them).
- **No cross-reference to `provisioning.md`** for creating locations or users (all features are location-scoped).
- **No cross-reference to `call-routing.md`**. Paging groups and voicemail groups have phone numbers that interact with the dial plan/routing chain.
- The Call Pickup section mentions feature access code `*98` (line 640) with a NEEDS VERIFICATION tag but doesn't reference `location-call-settings-core.md` or `location-call-settings-advanced.md` where feature access codes might be documented.

### 2.4 NEEDS VERIFICATION Tags

| Line | Tag Content | Assessment |
|------|-------------|------------|
| 39 | `<!-- NEEDS VERIFICATION: exact attribute names on api.telephony for callpark, callpark_extension, callpickup -->` | **Resolvable.** The SDK access paths listed (`api.telephony.callpark`, `api.telephony.callpark_extension`, `api.telephony.callpickup`) match the naming convention used in call-features-major.md (`api.telephony.auto_attendant`, `api.telephony.callqueue`, `api.telephony.huntgroup`). Can likely be confirmed by checking the SDK source or testing `dir(api.telephony)`. Remove tag if confirmed. |
| 642 | `<!-- NEEDS VERIFICATION: exact feature access code for call pickup -->` | **Not resolvable from other docs.** `*98` is the common Cisco/Webex default FAC for directed call pickup, but BroadWorks-based systems vary. Might be documented in `location-call-settings-core.md` or `location-call-settings-advanced.md` under Feature Access Codes. Check those files. |
| 650 | `<!-- NEEDS VERIFICATION: one-pickup-group-per-user constraint -->` | **Not resolvable from docs alone.** This is a platform constraint that needs API testing or Cisco documentation confirmation. Keep tag. |
| 811 | `<!-- NEEDS VERIFICATION: undocumented field -->` (VoicemailGroupDetail.time_zone) | **Partially resolvable.** Time zone fields appear on every location-scoped feature (AA, CQ, HG). Likely inherited from the location if not set. Keep tag but add note "Likely inherits from location if unset, consistent with AA/CQ/HG behavior." |

### 2.5 Formatting

- Structure is consistent with call-features-major.md in spirit but uses a **different layout**: each feature uses Overview > SDK API Class > API Operations (individual method signatures in code blocks) > Key Data Models > Phone Number Assignment > Member Management. In contrast, call-features-major.md uses Overview > SDK access path > API Operations (table) > Key Data Models (tables).
- **Inconsistency**: call-features-major.md presents API operations as compact tables; call-features-additional.md presents them as individual code blocks with docstring-style descriptions. The code-block style is arguably more readable for this doc since the signatures are simpler, but the inconsistency between the two companion docs is notable.
- **Recommendation**: Standardize. Either both use tables, or both use code blocks. Since the major features have complex signatures with many parameters, tables work well there. Since additional features have simpler signatures, code blocks work well. If keeping both styles, add a brief note in each doc explaining the format choice.
- The Data Models Quick Reference (line 1124) and Dependencies & Relationships (line 1153) sections at the end are excellent -- call-features-major.md lacks an equivalent dependency diagram. Consider adding one there too.

---

## 3. call-routing.md

### 3.1 Accuracy

**Method signatures** -- All present with correct types. Notable details:
- `DialPlanApi.create()` returns `CreateResponse` (not just `str`) which includes `dial_pattern_errors` -- correctly documented.
- `TrunkApi.create()` documents the certificate-based trunk parameters (`address`, `domain`, `port`, `max_concurrent_calls`) as conditional requirements.
- `RouteListApi.list()` accepts `list[str]` for `name` and `location_id` -- unusual multi-value filter correctly documented.

**Scopes** -- Correctly splits:
- `spark-admin:telephony_config_read`/`write` for dial plans, trunks, route groups, route lists, translation patterns, PNC.
- `spark-admin:telephony_pstn_read`/`write` for PSTN connection configuration.

**Data models** -- Comprehensive. All major models documented: `DialPlan`, `Trunk`, `TrunkDetail`, `RouteGroup`, `RGTrunk`, `RouteList`, `RouteListDetail`, `TranslationPattern`, `PSTNConnectionOption`, `RouteIdentity`, `TestCallRoutingResult`, and all supporting enums.

**The dial plan -> route list -> route group -> trunk chain**: Explained in the Architecture Overview (lines 29-53) with both a diagram and a 7-point narrative. The Complete End-to-End Setup Flow (lines 1342-1368) provides the implementation order. Both are accurate and complementary.

### 3.2 Gaps

**All major features covered**: Dial Plans, Trunks, Route Groups, Route Lists, Translation Patterns, PSTN Configuration, PNC, Route Choices, Call Routing Test, Phone Number Management.

**Missing items**:
- **Trunk update limitations**: The `TrunkApi.update()` doc (line 434) notes that `name` and `password` are always required, but doesn't mention that you CANNOT change `trunk_type`, `location_id`, or `device_type` after creation. This is a critical operational detail.
- **Route group trunk limit**: Mentioned in the overview ("up to 10 trunks") but not enforced or noted in the `RouteGroupApi.create()` section.
- **Dial plan pattern limit**: No mention of any limit on the number of patterns per dial plan (Webex Calling has a limit, typically 10,000 patterns per org).
- **`CallSourceInfo` model**: Referenced in `TestCallRoutingResult.call_source_info` (line 1165) and used in the test example (lines 1236-1242) but never defined with its field table. The example shows `call_source_type`, `route_list_name`, `dial_plan_name`, `dial_pattern` -- these should be documented formally.
- **`AppliedService` model**: Referenced in `TestCallRoutingResult.applied_services` (line 1182) and briefly described (line 1185) but no field table. The example shows `translation_pattern` sub-object with `matching_pattern`, `replacement_pattern`, `matched_number`, `translated_number` -- document these.
- **Destination-specific models**: `HostedUserDestination`, `HostedFeatureDestination`, `PbxUserDestination`, `PstnNumberDestination`, `VirtualExtensionDestination`, etc. are all referenced in `TestCallRoutingResult` (lines 1170-1181) but none are documented. The test example (line 1218) shows `pstn_number.trunk_name` and `pstn_number.route_group_name` but the full model is unknown.
- **Translation pattern wildcard syntax**: The doc covers dial plan pattern wildcards (`!`, `X`) in detail but doesn't cover translation pattern replacement syntax. How does `9XXX` -> `XXX` work? Are the X positions preserved positionally? Is there a `\1` or `$1` backreference syntax? This is critical for anyone writing translation patterns.

### 3.3 Cross-References

**Present**:
- Architecture Overview implicitly references the full chain from dial plan through trunk to PSTN.
- End-to-End Setup Flow (Section 15) ties all sections together sequentially.

**Missing**:
- **No cross-reference to `provisioning.md`** for locations. Trunks are location-scoped; route lists are location-scoped; PSTN configuration is per-location. The doc assumes locations exist but doesn't point to where you create them.
- **No cross-reference to `call-features-major.md`**. The call routing test result includes `HOSTED_FEATURE` destination type (line 1144) which covers auto-attendants, hunt groups, and call queues -- a cross-reference here would help readers understand what feature types map to this destination.
- **No cross-reference to `emergency-services.md`**. The call routing test result includes `EMERGENCY` destination type (line 1151) but no pointer to the emergency services configuration doc.
- **No cross-reference to `call-features-additional.md`** or `virtual-lines.md` for the entities that can be assigned phone numbers from the phone number management section.

### 3.4 NEEDS VERIFICATION Tags

**None found.** The call-routing doc has zero NEEDS VERIFICATION tags, which is unusual and suggests high confidence in the content. However, per the gaps identified above, there are undocumented models (`CallSourceInfo`, `AppliedService`, destination-specific models) that should arguably be tagged if the author was uncertain about their exact fields.

### 3.5 Formatting

- Consistent structure throughout: Data Models (code blocks) > API Methods (individual code blocks) > Usage Example.
- Clean separation between sections with `---` dividers.
- Architecture diagram and End-to-End Setup Flow diagram are both present and helpful.
- **Inconsistency with the call-features docs**: call-routing.md presents data models primarily as Python class definitions in code blocks, while call-features-major.md uses markdown tables. Both are readable, but the inconsistency across the reference doc set is notable.
- **Recommendation**: The code-block approach in call-routing.md is well-suited for routing models (which have many Optional fields and aliases), while the table approach in call-features-major.md works better for feature models (where required-for-create is important). Consider standardizing on one approach or documenting the rationale.

---

## Summary of Findings

### Critical Issues (should fix)

| # | File | Issue |
|---|------|-------|
| 1 | call-features-additional | `CallRecordingSetting` model used by CX Essentials queue recording is never defined. Readers cannot implement queue recording without field documentation. |
| 2 | call-features-additional | Voicemail Group sub-models (`VoicemailMessageStorage`, `VoicemailNotifications`, `VoicemailFax`, `VoicemailTransferToNumber`, `VoicemailCopyOfMessage`) referenced as required but never documented. |
| 3 | call-routing | `CallSourceInfo`, `AppliedService`, and all destination-specific models (`HostedUserDestination`, `PstnNumberDestination`, etc.) referenced in `TestCallRoutingResult` but never documented. |
| 4 | call-routing | Translation pattern replacement syntax not explained. Readers cannot write translation patterns without understanding how matching_pattern maps to replacement_pattern. |

### Important Issues (should fix before use)

| # | File | Issue |
|---|------|-------|
| 5 | call-features-major | Feature Comparison appendix: max agent rows conflate WEIGHTED (100) with CIRCULAR/REGULAR/UNIFORM (1,000). Split the rows. |
| 6 | call-features-major | HG holiday/night service rows marked NEEDS VERIFICATION are resolvable: HGs use forwarding rules with schedule-based triggers, not a dedicated policy API. Update text and remove tags. |
| 7 | call-routing | Trunk update limitations not documented (cannot change trunk_type, location_id, or device_type post-creation). |
| 8 | All three files | No cross-references to `provisioning.md` for location/user prerequisites. |
| 9 | call-features-major/additional | No cross-references between the two companion docs (e.g., Call Park recall -> Hunt Groups, VM Groups -> AA/CQ/HG overflow). |
| 10 | call-features-major/additional | No cross-references to `call-routing.md` for phone number routing implications. |

### Minor Issues (nice to have)

| # | File | Issue |
|---|------|-------|
| 11 | call-features-major | No code example for AA menu configuration (CQ agent management and HG agent management have examples). |
| 12 | call-features-major | CQ callback feature deserves behavioral explanation beyond the field listing. |
| 13 | call-features-major | CQ supervisor actions (barge-in, monitoring, coaching) mentioned in org settings but no cross-reference to call-control.md. |
| 14 | call-features-additional | Formatting inconsistency: uses code blocks for API methods vs. tables in call-features-major.md. |
| 15 | call-features-additional | `PersonPlaceAgent` fields not documented inline (only in quick reference table). |
| 16 | call-routing | Route group 10-trunk limit mentioned in overview but not in create method docs. |
| 17 | call-routing | Dial plan pattern-per-org limit not documented. |

### NEEDS VERIFICATION Tag Summary

| File | Tag Count | Resolvable | Action |
|------|:---------:|:----------:|--------|
| call-features-major | 3 | 2 of 3 | Lines 711/712 (HG holiday/night) resolvable from forwarding API docs -- update and remove. Line 323 (agent type bug) keep. |
| call-features-additional | 4 | 1 of 4 | Line 39 (SDK attr names) likely resolvable via SDK inspection. Lines 642, 650 keep. Line 811 keep with added note. |
| call-routing | 0 | n/a | Clean, but destination-specific models should arguably be tagged since their fields are undocumented. |
| **Total** | **7** | **3** | |

### Cross-Reference Recommendations

Add these cross-references:

1. **call-features-major.md Section 7 (Dependencies)**:
   - "Locations must exist -- see [Provisioning Reference](provisioning.md) for location creation."
   - "Agents must be existing users -- see [Provisioning Reference](provisioning.md) for people management."

2. **call-features-major.md Section 2 (Call Queues)**:
   - In overflow section: "Voicemail groups can be used as overflow destinations -- see [Additional Call Features](call-features-additional.md#voicemail-groups)."
   - In CQ overview or org settings: "Supervisor actions (barge-in, silent monitoring, coaching) are executed via the Call Control API -- see [Call Control Reference](call-control.md)."

3. **call-features-major.md Section 3 (Hunt Groups)**:
   - "Hunt groups can be used as Call Park recall targets -- see [Call Park](call-features-additional.md#call-park)."

4. **call-features-additional.md Dependencies section**:
   - "All features require a location -- see [Provisioning Reference](provisioning.md)."
   - "Call Park recall references hunt groups from [Major Call Features](call-features-major.md#3-hunt-groups)."
   - "CX Essentials extends call queues from [Major Call Features](call-features-major.md#2-call-queues)."

5. **call-routing.md Architecture Overview or PSTN Configuration**:
   - "Locations must exist before configuring PSTN connections -- see [Provisioning Reference](provisioning.md)."
   - "The `HOSTED_FEATURE` destination type in call routing test results includes auto attendants, call queues, and hunt groups -- see [Major Call Features](call-features-major.md)."
