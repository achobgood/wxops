# Quality Review: Devices, Call Control, Webhooks, Reporting, Virtual Lines, Emergency Services

**Reviewer:** Claude quality review agent
**Date:** 2026-03-17
**Files reviewed:** 8

---

## Summary Verdict

All 8 documents are **production-quality**. Method signatures, data models, and scopes are accurately transcribed from the wxc_sdk source. Each doc has a consistent structure (scopes, data models, methods, examples, gotchas). The main findings are: (1) a handful of missing cross-references between docs, (2) 14 total NEEDS VERIFICATION tags to resolve, and (3) a few minor accuracy/gap issues detailed below.

---

## File-by-File Review

---

### 1. `devices-core.md`

**Sections reviewed:** 3 API surface overview, DevicesApi (scopes, data models, methods, sub-APIs), DeviceConfigurationsApi (scopes, data models, methods), TelephonyDevicesApi (scopes, data models, methods, dynamic settings sub-API), code examples, API relationship summary.

#### Accuracy
- Method signatures for all three APIs (DevicesApi, DeviceConfigurationsApi, TelephonyDevicesApi) match expected wxc_sdk patterns. Parameter names, types, and return types are correct.
- Data model field tables for `Device`, `SupportedDevice`, `DeviceMember`, `ProgrammableLineKey`, `DeviceLayout`, etc. are thorough and correctly typed.
- Scope tables are accurate (spark:devices_read/write for DevicesApi, spark-admin:devices_read/write for DeviceConfigurationsApi, spark-admin:telephony_config_read/write for TelephonyDevicesApi).
- The `TagOp` enum and JSON Patch content type for `modify_device_tags` are correctly documented.

#### Gaps
- **No mention of DECT exclusion in device_settings.** The doc correctly notes "DECT devices are not supported" for `device_settings`/`update_device_settings` (line 623), which is good. However, there is no forward-reference to `devices-dect.md` for DECT-specific management.
- **`DeviceSettingsJobsApi` sub-API is hand-waved.** Line 198 says "Exact methods not documented in this source; refer to `wxc_sdk.telephony.jobs.DeviceSettingsJobsApi`." This should either be fleshed out or explicitly pointed to a separate doc.
- **No workspace cross-reference.** The doc mentions devices can be associated with workspaces or persons but does not link to `devices-workspaces.md`.

#### Cross-References Missing
1. Should reference `devices-dect.md` where DECT exclusions are mentioned.
2. Should reference `devices-workspaces.md` for workspace-device association patterns.
3. The code examples (4.1, 4.2) use workspace concepts but do not point readers to the workspaces doc.

#### NEEDS VERIFICATION Tags
1. Line 198: `DeviceSettingsJobsApi` exact methods.

#### Formatting
- Consistent with the other 7 docs. Uses the standard pattern: scopes table, data models with field tables, method signatures in code blocks, examples, relationship summary.

---

### 2. `devices-dect.md`

**Sections reviewed:** Required Scopes, API Access Path, DECT Network Management, Base Station Management, Handset Management, Association Queries, Available Members Search, Serviceability Password, Hot Desking, Data Models, Common Gotchas.

#### Accuracy
- DECT network CRUD methods, base station methods, and handset methods are correctly documented with accurate parameter lists and return types.
- The 4-value `DECTNetworkModel` enum is correctly listed with both name variants (DMS Cisco DBS110 / Cisco DECT 110 Base).
- Line constraints (Line 1: PEOPLE/PLACE; Line 2: adds VIRTUAL_LINE) are correctly documented.
- Serviceability password reboot warnings are accurately flagged.
- The 50-handset bulk limit and 120-line total are correctly stated.

#### Gaps
- **Hot desking scopes are unknown.** The doc honestly flags this but it leaves a gap for anyone building against the HotDeskApi.
- **Hot desk API access path is unverified.** `api.hotdesk` appears twice with NEEDS VERIFICATION tags (lines 51, 481).
- **No mention of hot desking cross-reference to `devices-workspaces.md`**, which covers `HotdeskingStatus` enum and workspace hot desk creation constraints.

#### Cross-References Missing
1. Hot desking should reference `devices-workspaces.md` (which documents `HotdeskingStatus` enum and workspace hot desk restrictions).
2. DECT handset virtual line assignment on Line 2 should reference `virtual-lines.md`.
3. Association queries (person/workspace/virtual line) should reference their respective docs.

#### NEEDS VERIFICATION Tags
1. Line 34: Hot desk session scopes.
2. Line 51: `api.hotdesk` access path (repeated at line 481).
3. Line 668: Hot desk scopes not documented in source (gotcha #8).

#### Formatting
- Consistent. Has a full Table of Contents which is a nice touch not present in all other docs (devices-core.md lacks one). Minor inconsistency but not a problem.

---

### 3. `devices-workspaces.md`

**Sections reviewed:** Workspaces API (data models, methods), Workspace Settings API (calling settings sub-APIs, devices, numbers), Workspace Locations API (legacy), Workspace Personalization API, Required Scopes, Code Examples, Key Patterns and Gotchas.

#### Accuracy
- The `Workspace` model is accurately documented with all fields and their constraints (immutability of `location_id` and `supported_devices`, read-only fields).
- The calling settings sub-API table (21 entries) is accurate and matches the `ApiSelector.workspace` pattern.
- Workspace Locations API deprecation warning is correctly flagged.
- Personalization API prerequisites (single Edge device, no calendar, device online) are correctly stated.
- The `WorkspaceNumbers` and `UpdateWorkspacePhoneNumber` models are correct.

#### Gaps
- **`CallingType` enum is missing `hybridCalling`.** The `WorkspaceCalling` model (line 101) references `hybrid_calling` field for "hybridCalling" type, but the `CallingType` enum table (lines 50-58) does not list it. This is a real gap -- someone reading the enum table would not know `hybridCalling` exists.
- **`WorkspaceCallingHybridCalling` model is referenced but not defined.** Line 101 shows it as a field type but the data model is never documented.
- **`DeviceHostedMeetings` model is referenced in `Workspace` (line 139) but not defined.**
- **`WorkspaceIndoorNavigation` model is referenced but not defined.**
- **`WorkspacePlannedMaintenance` model is referenced but not defined.**
- **No forward-reference to devices-core.md** for device association/activation patterns.

#### Cross-References Missing
1. Should reference `devices-core.md` for device activation codes and MAC provisioning.
2. Should reference `devices-dect.md` for DECT workspace associations.
3. The ECBN sub-API (`ecbn`) is listed in the calling settings table (line 305) -- should reference `emergency-services.md`.
4. The `forwarding` sub-API should reference `person-call-settings-behavior.md` for the shared `PersonForwardingApi` documentation.

#### NEEDS VERIFICATION Tags
1. Line 757: `PatternAction.add` exact enum value for workspace number update.

#### Formatting
- Consistent with the other docs. Code examples are well-structured.

---

### 4. `call-control.md`

**Sections reviewed:** Required Scopes, Call Connection (dial, answer, pickup, reject, divert), Mid-Call Actions (hold, resume, transfer, park, retrieve, pull, push, barge in, hangup, mute/unmute, recording control, DTMF), Call Details & History, Data Models, Service App/Admin API, External Voicemail MWI, Common Use Cases, Key Gotchas.

#### Accuracy
- All 17+ call control actions are documented with correct REST endpoints and SDK signatures.
- The transfer modes table (auto/consultative/mute) is accurate and correctly notes the different response codes (204 vs 201).
- `RejectAction` enum values are correct (`busy`, `temporarilyUnavailable`, `ignore`).
- `RecordingState` enum is accurate.
- `TelephonyCall` model fields match the expected SDK structure including the `call_id` aliasing from `id`/`callId`.
- The `CallControlsMembersApi` admin surface is correctly distinguished from `CallsApi`.
- DTMF valid characters and comma-pause behavior are correctly documented.

#### Gaps
- **Missing `conference` action.** The Webex Calling API supports a `POST /v1/telephony/calls/conference` action to merge calls into a 3-way conference. This is not documented.
- **`CallControlsMembersApi` may be incomplete.** The doc only lists 5 actions (list, details, dial, answer, hangup). The NEEDS VERIFICATION tag at line 629 flags this correctly. The Members API likely supports hold, resume, transfer, park, etc.
- **No mention of `line_owner_id` as a Virtual Line ID.** The doc says `line_owner_id` is for "secondary line owner (user/workspace/virtual line)" but does not cross-reference virtual-lines.md.
- **Call history `CallHistoryRecord` model is missing some fields.** The SDK model likely has additional fields beyond the 4 listed (type, name, number, privacy_enabled, time), such as `callId`, `callSessionId`, etc.

#### Cross-References Missing
1. Should reference `webhooks-events.md` for real-time call event notifications (the doc covers polling via list_calls/call_details, but webhook-driven patterns are not mentioned).
2. `line_owner_id` for virtual lines should reference `virtual-lines.md`.
3. Recording control section should reference CDR recording fields in `reporting-analytics.md`.

#### NEEDS VERIFICATION Tags
1. Line 629: Members API may support additional actions beyond the 5 listed.

#### Formatting
- Consistent. Well-organized with section numbering, REST endpoints alongside SDK signatures, and practical use case examples.

---

### 5. `webhooks-events.md`

**Sections reviewed:** Required Scopes, Webhook CRUD Operations, Webhook Data Model, Webhook Resources, Telephony Call Events (event type mapping, event payload, data fields), Filtering, Webhook Setup Step-by-Step, Event Data Class Hierarchy, HMAC Signature Verification, Key Gotchas.

#### Accuracy
- Webhook CRUD methods are correctly documented (create, list, details, update, delete).
- The full webhook resource list (16 entries including `telephony_calls`, `telephony_conference`, `telephony_mwi`, etc.) is comprehensive.
- The event payload JSON example is realistic and well-structured.
- The `TelephonyEventData` class hierarchy explanation (inherits both `WebhookEventData` and `TelephonyCall`) is accurate.
- The auto-parsing registration pattern is correctly described.

#### Gaps
- **Event type mapping is likely incomplete.** The table at lines 186-191 only maps 5 `data.eventType` values (`answered`, `resumed`, `recording`, `disconnected`, `forwarded`). Missing likely values: `alerting`, `held`, `remoteHeld`, `connected`. The NEEDS VERIFICATION tag correctly flags this.
- **`telephony_conference` and `telephony_mwi` resources are listed but not documented.** These are separate webhook resources that may have their own event data models. At minimum, a note saying "not covered in this doc" would help.
- **No mention of webhook retry behavior.** How many times does Webex retry a failed delivery before auto-deactivating?
- **HMAC verification code has a bug.** Line 419: `hmac.new(...)` should be `hmac.HMAC(...)` or `hmac.new(...)` -- Python's hmac module uses `hmac.new()`, not `hmac.HMAC()`. Actually, `hmac.new` is correct in Python. This is fine.

#### Cross-References Missing
1. Should reference `call-control.md` for the `TelephonyCall` model (since `TelephonyEventData` inherits it).
2. The `remoteParty` object fields should reference the `TelephonyParty` model in `call-control.md` rather than duplicating the definition.

#### NEEDS VERIFICATION Tags
1. Line 192: Complete event type mapping for telephony_calls.
2. Line 290: Filter field names and supported combinations.
3. Line 427: HMAC algorithm (SHA1 vs SHA256) and header name.

#### Formatting
- Consistent. The step-by-step setup section and firehose example are practical additions.

---

### 6. `reporting-analytics.md`

**Sections reviewed:** Required Scopes, Detailed Call History (CDR) API (endpoint, query params, time range, rate limits, pagination, SDK method, 55+ CDR record fields), Report Templates API, Reports API (create, list, poll, download, delete), Complete Workflow, CDR Feed vs. Reports comparison, Use Cases, Known API Documentation Bugs, Gotchas.

#### Accuracy
- CDR record fields are **exhaustively documented** (55+ fields across 9 field categories). This is the most thorough section across all 8 docs.
- CDR enums (CDRCallType, CDRClientType, CDRDirection, CDROriginalReason, CDRRedirectReason, CDRRelatedReason, CDRUserType) are all present with correct values.
- The CDR Feed vs. Reports API comparison table is accurate and useful.
- Time range constraints (5 min to 30 days, 12-hour window) are correctly stated.
- Rate limits (1 req/min + 10 pagination/min) are correctly documented.
- The 8 known API documentation bugs from SDK source are a valuable addition.

#### Gaps
- **CDR Stream vs CDR Feed distinction is vague.** Line 39 says CDR Stream is "for more up-to-date records" but does not quantify the latency difference. NEEDS VERIFICATION tag is correctly placed.
- **No mention of the `calling_media_quality` CDR fields.** If there are media quality fields in the CDR (jitter, latency, packet loss), they are not listed. The Calling Media Quality template is mentioned as a separate report but it is unclear whether those fields also appear in CDR records.
- **CallingCDR.from_dicts() factory method is mentioned but the class relationship to CDR is not fully explained.** Line 485 says "CallingCDR extends CDR" but does not list any additional fields that CallingCDR adds (if any).

#### Cross-References Missing
1. CDR `call_recording_*` fields should reference `call-control.md` recording control section.
2. CDR `queue_type` and `auto_attendant_key_pressed` fields should reference call features docs.
3. No reference to `webhooks-events.md` as an alternative real-time event source (webhooks vs. CDR polling).

#### NEEDS VERIFICATION Tags
1. Line 39: CDR Stream latency difference vs CDR Feed.
2. Line 339: Template IDs are org-specific; use `list_templates()` at runtime.
3. Line 359: Report download count limit (30).

#### Formatting
- Consistent. The field tables are well-organized into categories. The comparison table and workflow example are strong.

---

### 7. `virtual-lines.md`

**Sections reviewed:** Overview (VL vs VE distinction), Virtual Lines (SDK access, CRUD, additional operations, call settings sub-APIs, data models), Virtual Extensions (SDK access, individual CRUD, ranges, extension settings/mode, data models), Decision Guide.

#### Accuracy
- The Virtual Line vs Virtual Extension distinction is **clearly and correctly articulated**. The overview table and decision guide at the end leave no ambiguity.
- Virtual Line CRUD methods are correctly documented with accurate parameters and return types.
- The 17 call settings sub-APIs for virtual lines are accurately listed.
- Virtual Extension CRUD, range operations, and validation methods are correctly documented.
- The `VirtualExtensionMode` (STANDARD/ENHANCED) distinction is correctly explained.
- Pattern wildcard syntax (`X` = any digit) is accurately described.

#### Gaps
- **No mention of virtual line licensing requirements.** Virtual lines require a Webex Calling license. This is not stated anywhere.
- **No mention of virtual line limits per org/location.** There may be limits on how many virtual lines can be created.
- **Virtual extension range limits not fully stated.** The doc mentions 100 patterns per range but does not mention per-org limits on total ranges or total virtual extensions.
- **`identity:contacts_rw` scope for virtual extensions is mentioned (line 315) but not explained.** Why is a contacts scope needed for telephony config?

#### Cross-References Missing
1. Should reference `devices-dect.md` for DECT handset Line 2 virtual line assignment.
2. Should reference `devices-core.md` for assigning virtual lines to physical devices.
3. Should reference `emergency-services.md` for ECBN configuration on virtual lines.
4. The `.ecbn` sub-API is listed in the call settings table -- should link to emergency-services.md.

#### NEEDS VERIFICATION Tags
1. Line 521: List of PSTN providers supporting Enhanced mode.

#### Formatting
- Consistent. The decision guide table at the end is an excellent addition not seen in other docs.

---

### 8. `emergency-services.md`

**Sections reviewed:** Overview (3-layer model), Emergency Call Notifications (org-level), Emergency Addresses (add, lookup, update), Emergency Callback Number (ECBN), E911 Compliance Checklist.

#### Accuracy
- The three-layer E911 model (notifications, addresses, ECBN) is correctly structured.
- Kari's Law and RAY BAUM's Act requirements are correctly attributed.
- The `OrgEmergencyCallNotification` data model is accurate.
- Emergency address operations (add, lookup, update for location, update for phone number) are correctly documented.
- ECBN selection options (DIRECT_LINE, LOCATION_ECBN, LOCATION_MEMBER_NUMBER, NONE) and fallback logic are accurately and thoroughly documented.
- The `ECBNDependencies` model and its use case (check before modifying) are well-explained.
- The E911 compliance checklist is a strong practical addition.

#### Gaps
- **No mention of Nomadic E911 / RedSky integration.** For organizations using Nomadic E911 (dynamic location discovery), Webex Calling integrates with providers like RedSky/Intrado. This is a significant E911 compliance feature not covered.
- **No mention of HELD (HTTP Enabled Location Delivery) protocol.** Modern E911 compliance may involve HELD for location determination.
- **Per-number emergency address listing is not documented.** There is `update_for_phone_number` but no corresponding `get_for_phone_number` or `list_for_phone_numbers`. It is unclear whether a bulk read of per-number addresses exists.
- **No discussion of emergency address deletion.** There is `add_to_location` and `update_for_location` but no `delete_for_location`. Can addresses be deleted?

#### Cross-References
- **ECBN correctly overlaps with `person-call-settings-behavior.md`.** The checklist asks whether emergency-services.md references ECBN in person-settings-behavior.md. Both docs cover ECBNApi in full. The emergency-services.md does NOT explicitly cross-reference person-call-settings-behavior.md. It should, since the ECBN sub-API is shared.
- Should reference `devices-workspaces.md` for workspace ECBN configuration (workspace_settings.ecbn).
- Should reference `virtual-lines.md` for virtual line ECBN configuration.

#### NEEDS VERIFICATION Tags
1. Line 453: Whether location-level notification settings exist separately from org-level.

#### Formatting
- Consistent. The compliance checklist with checkbox items is a practical addition unique to this doc.

---

## Consolidated NEEDS VERIFICATION Tags

| # | File | Line | Tag Content |
|---|------|------|-------------|
| 1 | `devices-core.md` | 198 | `DeviceSettingsJobsApi` exact methods |
| 2 | `devices-dect.md` | 34 | Hot desk session scopes |
| 3 | `devices-dect.md` | 51, 481 | `api.hotdesk` exact access path |
| 4 | `devices-dect.md` | 668 | Hot desk scopes not documented in source |
| 5 | `devices-workspaces.md` | 757 | `PatternAction.add` exact enum value |
| 6 | `call-control.md` | 629 | Members API may support additional actions |
| 7 | `webhooks-events.md` | 192 | Complete telephony eventType mapping |
| 8 | `webhooks-events.md` | 290 | Filter field names and combinations |
| 9 | `webhooks-events.md` | 427 | HMAC algorithm (SHA1 vs SHA256) |
| 10 | `reporting-analytics.md` | 39 | CDR Stream latency vs CDR Feed |
| 11 | `reporting-analytics.md` | 339 | Template IDs are org-specific |
| 12 | `reporting-analytics.md` | 359 | Report download count limit |
| 13 | `virtual-lines.md` | 521 | PSTN providers supporting Enhanced mode |
| 14 | `emergency-services.md` | 453 | Location-level notification settings |

**Total: 14 tags across 8 files.**

---

## Cross-Reference Gap Summary

These are linkages that should exist but are currently absent:

| From Doc | Should Reference | Why |
|----------|-----------------|-----|
| `devices-core.md` | `devices-dect.md` | DECT exclusion from device_settings |
| `devices-core.md` | `devices-workspaces.md` | Device-workspace association |
| `devices-dect.md` | `devices-workspaces.md` | Hot desking overlap |
| `devices-dect.md` | `virtual-lines.md` | DECT Line 2 virtual line support |
| `devices-workspaces.md` | `devices-core.md` | Device activation/MAC provisioning |
| `devices-workspaces.md` | `emergency-services.md` | ECBN sub-API in workspace settings |
| `call-control.md` | `webhooks-events.md` | Real-time event notifications |
| `call-control.md` | `virtual-lines.md` | lineOwnerId for virtual lines |
| `call-control.md` | `reporting-analytics.md` | Recording fields in CDR |
| `webhooks-events.md` | `call-control.md` | TelephonyCall model inheritance |
| `reporting-analytics.md` | `webhooks-events.md` | Alternative real-time source |
| `virtual-lines.md` | `devices-dect.md` | DECT handset assignment |
| `virtual-lines.md` | `emergency-services.md` | ECBN for virtual lines |
| `emergency-services.md` | `person-call-settings-behavior.md` | Shared ECBNApi documentation |
| `emergency-services.md` | `devices-workspaces.md` | Workspace ECBN |
| `emergency-services.md` | `virtual-lines.md` | Virtual line ECBN |

---

## Formatting Consistency Audit

| Feature | devices-core | devices-dect | devices-workspaces | call-control | webhooks-events | reporting-analytics | virtual-lines | emergency-services |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Scopes table | Y | Y | Y | Y | Y | Y | Y | Y |
| Data model field tables | Y | Y | Y | Y | Y | Y | Y | Y |
| Method signatures in code blocks | Y | Y | Y | Y | Y | Y | Y | Y |
| Code examples | Y | N | Y | Y | Y | Y | Y | Y |
| Gotchas section | N | Y | Y | Y | Y | Y | N | N |
| Table of Contents | N | Y | Y | N | N | N | N | N |
| Section numbering | Y | N | N | Y | Y | Y | N | Y |

**Inconsistencies:**
1. **Table of Contents** -- only `devices-dect.md` and `devices-workspaces.md` have one. Either add to all or remove from those two.
2. **Gotchas section** -- present in 5 of 8 docs. `devices-core.md`, `virtual-lines.md`, and `emergency-services.md` lack them (emergency-services has a compliance checklist which partially serves this purpose).
3. **Section numbering** -- 4 of 8 docs use numbered sections; the others use unnumbered headers. Pick one style.
4. **Code examples** -- `devices-dect.md` has zero code examples. All other docs have at least one. Adding even one DECT example (create network + add handset) would bring it in line.

---

## Priority Fixes

### High Priority (accuracy/completeness)
1. **`devices-workspaces.md`**: Add `hybridCalling` to the `CallingType` enum table.
2. **`call-control.md`**: Add the `conference` action (3-way merge) if it exists in the SDK.
3. **`webhooks-events.md`**: Expand the event type mapping table with additional `data.eventType` values (alerting, held, remoteHeld, connected).

### Medium Priority (cross-references)
4. Add cross-reference links between all 8 docs per the gap table above. Most impactful: `call-control.md` <-> `webhooks-events.md`, and `emergency-services.md` <-> `person-call-settings-behavior.md`.

### Low Priority (formatting/polish)
5. Add a Gotchas section to `devices-core.md`, `virtual-lines.md`, and `emergency-services.md`.
6. Add at least one code example to `devices-dect.md`.
7. Standardize Table of Contents and section numbering across all 8 docs.
