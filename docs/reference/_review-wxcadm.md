# wxcadm Reference Docs -- Quality Review Report

Reviewed 2026-03-17. Covers all 8 wxcadm reference documents.

---

## 1. wxcadm-core.md

### Accuracy
- **Webex constructor**: Signature and parameter table are accurate. `fast_mode`, `read_only`, `org_id`, `auto_refresh_token` all documented correctly.
- **Org class**: Constructor signature matches. Lazy-loaded vs. non-cached vs. computed property classifications look correct.
- **WebexApi**: Method signatures are correct. The two-instance pattern (Webex-level + Org-level) is clearly explained.
- **Legacy webex_api_call()**: Correctly flagged as deprecated-in-practice. Good guidance to prefer `WebexApi`.
- **Exception hierarchy**: Tree is correct. `XSIError > NotAllowed` and `CSDMError` branches documented.
- **WebexLicenseList**: Type detection logic ("Professional" -> `professional`, etc.) is documented.

### Gaps
- The `Webex` constructor lists `get_xsi` as a parameter in the XSI doc (wxcadm-xsi-realtime.md line 68: `wxcadm.Webex(access_token, get_xsi=True)`) but it is **not listed** in the constructor signature in wxcadm-core.md. One of these is wrong -- either the constructor accepts `get_xsi` and it's missing from core, or the XSI doc is using a non-existent parameter. **Must verify.**
- `Org.roles` attribute is referenced by `Person.role_names()` but never listed as an Org attribute or property. Confirm whether it exists.
- `Org.applications` is listed under "Non-Cached Properties" but the quickstart section shows `developer_webex.org.applications.create_service_application(...)` -- this is consistent.
- Package exports section could list version info (`wxcadm.__version__`) if it exists.

### wxcadm vs wxc_sdk
- Comparison table is solid. CPAPI line correctly tagged `<!-- NEEDS VERIFICATION -->`.
- "When to use" guidance is practical and accurate.

### Bugs Documented
- `auto_refresh_token` flagged as "still in development -- do not use" -- good.

### Cross-references
- References wxc_sdk comparison table inline. Does not link to any specific wxc_sdk doc file.

### Formatting
- Consistent heading hierarchy, code blocks, tables. No issues.

---

## 2. wxcadm-person.md

### Accuracy
- **PersonList**: Constructor, `get()`, `create()`, `webex_calling()`, `recorded()` -- all signatures look correct.
- **Person**: Instance attributes table is thorough. Settings dicts table linking each to its `get_*` method is helpful.
- **Call Settings**: All 13 get/push pairs documented: voicemail, call forwarding, caller ID, call recording, call intercept, DND, calling behavior, hoteling, PTT, executive assistant, application services, barge-in, outgoing permission.
- **set_caller_id()**: The keyword mapping table (`"direct"` -> `DIRECT_LINE`, etc.) is a useful detail.
- **enable_call_recording()**: Parameter list includes `transcribe` and `ai_summary` -- newer parameters that confirm this was written against recent source.
- **ApplicationServicesSettings**: Full dataclass with setter methods documented.
- **ApplicationLineAssignments / ApplicationLine**: CRUD methods documented with `set_hotline`, `set_call_decline`, `set_label`, `delete`.
- **SingleNumberReach / SnrNumber**: Full CRUD documented.

### Gaps -- Call Settings Coverage
The doc claims to cover person call settings. Counting against the "34 call settings" target:

**Documented (with get/push or property):**
1. Voicemail (get/push + 7 convenience methods)
2. Call Forwarding (get/push)
3. Caller ID (get/push + set_caller_id)
4. Call Recording (get/push + enable/disable)
5. Call Intercept (get/push)
6. Do Not Disturb (get/push)
7. Calling Behavior (get/push)
8. Hoteling (get/push)
9. Push-to-Talk (get/push)
10. Executive Assistant (get/push)
11. Application Services (get/push + property)
12. Barge-In (property)
13. Single Number Reach (property)
14. Outgoing Permission (get/push)
15. Preferred Answer Endpoint (property + set)
16. Available Answer Endpoints (property)
17. ECBN (property + set + null_change)
18. Monitoring (property)
19. wxc_numbers (property)

**Not documented (likely not in wxcadm source):**
- Call Waiting
- Selective Call Forwarding (rules-based)
- Selective Call Acceptance / Rejection
- Anonymous Call Rejection (exposed via XSI only, noted in XSI doc)
- Sequential Ring
- Simultaneous Ring
- Priority Alert
- Incoming Call Notification
- Connected Line ID Restriction (COLR)
- Calling Line ID Restriction (CLIR)
- Music on Hold (person-level)
- Receptionist Client
- Call Bridge
- Agent Join/Unjoin (CQ-specific)
- Executive settings (vs executive assistant)

The "34" figure likely refers to the Webex API's full person settings count. The doc covers what wxcadm implements (19 settings) -- this is fine, but should explicitly note which settings are NOT covered by wxcadm.

### wxcadm vs wxc_sdk
- Table is detailed. Multiple `<!-- NEEDS VERIFICATION -->` tags on wxc_sdk equivalents for ECBN, SNR, Application Line Assignments, User Groups, Voice Messages. Appropriate.

### Bugs Documented
1. `role_names()` -- return inside for loop (only first role returned). Tagged `<!-- NEEDS VERIFICATION -->`.
2. `SnrNumber.set_do_not_forward_calls()` -- copy-paste bug setting wrong attribute. Tagged `<!-- NEEDS VERIFICATION -->`.

Both are clearly flagged. Good.

### Formatting
- Table of Contents with anchor links. Consistent code blocks and tables throughout.

---

## 3. wxcadm-locations.md

### Accuracy
- **LocationList**: Constructor, `get()`, `create()`, `webex_calling()`, `with_pstn()` / `without_pstn()` -- all correct.
- **Location**: Constructor parameters match. Core properties table is accurate.
- **Calling Enablement**: `calling_enabled` property + setter, `enable_webex_calling()` with the `address2` gotcha -- good detail.
- **Calling Configuration**: `external_caller_id_name`, `routing_prefix`, `set_announcement_language()` with `update_users`/`update_features` flags -- correctly documented.
- **Number Management**: `numbers`, `available_numbers`, `main_number`, `set_main_number` -- all present.
- **Emergency Services**: `ecbn`, `set_ecbn`, `enhanced_emergency_calling`, `set_enhanced_emergency_calling` with the compliance warning gotcha.
- **Schedules**: `LocationSchedule` with `add_holiday()`, `create_event()`, `update_event()`, `delete_event()`, `clone()`.
- **Location Features**: VoicePortal, CallParkExtension, PagingGroup, OutgoingPermissionDigitPattern, VoicemailGroup -- all documented.
- **Floor Management**: `LocationFloorList` with `create()` and `LocationFloor` with `update()`/`delete()`.
- **Delete stub**: Correctly documents that `delete()` always returns `False`.

### Gaps
- `Location.calling_config` property is documented but the full shape of the returned dict is not described. Acceptable for a reference doc.
- `Location.unknown_extension_policy` setter accepts `Trunk | RouteGroup | str` -- cross-references call routing module.
- `Location.recording_vendor` is listed but not documented beyond its type. The full `LocationRecordingVendorSelection` class is in wxcadm-features.md -- should cross-reference.

### wxcadm vs wxc_sdk
- Comparison covers location access, calling enablement, architectural differences, schedule management. Appropriate `<!-- NEEDS VERIFICATION -->` tags on wxc_sdk delete support and schedule management.

### Bugs Documented
- `update_event()` truncated API URL flagged as `<!-- NEEDS VERIFICATION -->`.
- `enable_webex_calling()` address2 gotcha documented.
- `set_enhanced_emergency_calling()` Control Hub compliance warning documented.

### Cross-references
- Links to LocationSchedule section, OutgoingPermissionDigitPattern section. No explicit cross-references to wxc_sdk docs.

### Formatting
- Consistent. Table of Contents present. Code examples included.

---

## 4. wxcadm-features.md

### Accuracy
- **Auto Attendant**: `AutoAttendantList.create()` full signature with all menu/dialing scope parameters. `AutoAttendant` lazy-loaded properties vs. immediate attributes clearly separated.
- **Call Queue**: `CallQueueList.create()` with `call_policies`/`queue_settings` dicts. `OrgQueueSettings` for CX Essentials features.
- **Hunt Group**: `HuntGroupList.create()` with `call_policies` default structure example. `HuntGroup.add_agent()` method with weight parameter.
- **Pickup Group**: Location-only scope correctly noted. Read-only limitation documented.
- **Announcements**: `AnnouncementList` with `get()`, `upload()`, `stats`. `Announcement` with `used_by`, `in_use`, `replace_file`, `delete`.
- **Playlists**: `PlaylistList` with `create()`. `Playlist` with `refresh()`, `delete()`, `replace_announcements()`, `assign_to_location()`, `locations`.
- **Recording**: Full coverage of `RecordingVendor`, `OrgRecordingVendorSelection`, `LocationRecordingVendorSelection`, `ComplianceAnnouncementSettings`, `RecordingList`, `Recording`.

### Gaps
- `CallQueue.add_agent` is correctly flagged as not implemented (`pass` in source).
- `AutoAttendant.copy_menu_from_template()` limitation (no CUSTOM announcements) documented.
- No mention of Call Queue supervisor features (barge-in, silent monitoring, coaching) beyond `OrgQueueSettings` tone flags.

### wxcadm vs wxc_sdk
- Comparison table has heavy `<!-- NEEDS VERIFICATION -->` tagging on wxc_sdk columns -- appropriate since wxc_sdk feature coverage is uncertain.
- "Known gaps in wxcadm" section lists all unimplemented features and bugs.

### Bugs Documented
1. `CallQueue.add_agent` -- not implemented (pass).
2. `OrgRecordingVendorSelection.set_failure_behavior` -- not implemented (returns False).
3. `HuntGroupList.get` uuid branch -- `.uppper()` typo.
4. `Playlist.__getattr__` -- `"fv1/..."` not an f-string.
5. `ComplianceAnnouncementSettings.push` -- double slash in location endpoint.
6. `PickupGroupList` -- no refresh/create/delete.

All clearly flagged with `<!-- NEEDS VERIFICATION -->`. Excellent documentation of known issues.

### Cross-references
- API URL Patterns table at the end is comprehensive. Common Patterns section explains shared list class interface and lazy-loading approaches.

### Formatting
- Consistent tables, code blocks, bug notes. "Known Bugs and Incomplete Features" summary section at the end is a strong addition.

---

## 5. wxcadm-devices-workspaces.md

### Accuracy
- **DeviceList**: `get()` with multiple lookup keys including `connection_status`. `create()` return dict documentation by scenario is valuable. `get_by_status()` grouping shortcuts documented.
- **Device**: Full attribute table. Properties (`calling_id`, `config`, `settings`, `layout`, `members`) documented. Methods (`apply_changes`, `delete`, `change_tags`).
- **SupportedDevice**: Comprehensive attribute list with KEM, layout, upgrade channel fields.
- **DeviceMemberList**: `add()` with ATA note, `available_members()`, `ports_available()`, `port_map()`.
- **DeviceMember**: All attributes plus `set_line_label()`, `set_hotline()`, `set_call_decline_all()`.
- **DeviceLayout**: Attributes and usage pattern.
- **DECT**: `DECTNetworkList`, `DECTNetwork`, `DECTBaseStation`, `DECTHandset` -- full CRUD documented.
- **Workspace**: `WorkspaceList.create()` with license types and workspace types. Properties and methods.
- **VirtualLine**: Full CRUD, lazy-loaded properties, `enable_call_recording()`.
- **Number Management**: `NumberList` with `get()`, `add()`, `validate()`. `Number` dataclass with owner resolution.

### Gaps
- `DeviceList` constructor is not explicitly shown. The access patterns section shows `DeviceList(org, parent=location)` but doesn't document the full constructor signature.
- `Device.settings` setter behavior -- does it auto-push to Webex or just set locally? Not fully clear.
- `Workspace.unassign_wxc()` limitation for phone-based workspaces is documented -- good.

### wxcadm vs wxc_sdk
- Side-by-side code examples for device management and workspace creation. Practical.
- Key differences table covers supported devices, create device, get members, add shared line, DECT, virtual line CRUD.
- `<!-- NEEDS VERIFICATION -->` on DECT and Virtual Line wxc_sdk equivalents.

### Bugs Documented
1. `VirtualLine.get_call_recording()` -- passes `'get'` as first arg to `self.org.api.get()`. Tagged `<!-- NEEDS VERIFICATION -->`.
2. `VirtualLine.delete()` -- returns `False` on success. Tagged `<!-- NEEDS VERIFICATION -->`.

### Cross-references
- References Webex Developer docs for layout format. Common patterns section with full provisioning examples.

### Formatting
- Consistent. Code examples are extensive and practical (workspace provisioning, shared line, DECT setup, bulk number add).

---

## 6. wxcadm-xsi-realtime.md

### Accuracy
- **Architecture overview**: XSI-Actions vs XSI-Events distinction is clearly drawn. The streaming architecture diagram is helpful.
- **Setup**: Two init approaches (get_xsi at init, or `get_xsi_endpoints()` later). Prerequisites (TAC activation, scopes) documented.
- **XSI Profile**: Profile dict keys documented. Registrations, services, individual service properties.
- **Call Control**: `new_call()`, `originate()`, `hold()`, `resume()`, `answer_call()`, `hangup()`, `transfer()` (with blind/VM/mute/attended variants), `conference()`, `park()`, `recording()`, `send_dtmf()`, `exec_push()`, `reconnect()`, `attach_call()`.
- **XSI-Events**: Architecture diagram with ChannelSet -> Channel -> daemon threads. The Python Queue pattern is well explained.
- **Channel Management**: Lifecycle (SRV lookup -> one channel per XSP -> heartbeats -> auto-refresh). Failure recovery documented.
- **XSICallQueue**: Call Queue call control via attach_call.
- **MonitoringList**: REST-based BLF management with add/remove/copy_to/copy_from/replace/clear.

### Gaps
- **Event subscription**: Only "Advanced Call" package is demonstrated. Other packages (Basic Call, Call Center, DND, etc.) are flagged as `<!-- NEEDS VERIFICATION -->`.
- **Complete event type list**: Flagged as `<!-- NEEDS VERIFICATION -->`. The doc lists the most common types but acknowledges incompleteness.
- **Call Queue call control subset**: Flagged as `<!-- NEEDS VERIFICATION -->`.
- **XSI `get_xsi` parameter**: As noted in the core review, this parameter appears in the XSI doc but not in the core doc's Webex constructor signature. One of these is wrong.
- **XSI Calls class** (`org.calls`): Listed as a non-cached property on Org in core doc, but not documented in the XSI doc. Should clarify relationship between `org.calls` (Org-level Calls instance) and `person.xsi.calls` (XSI per-user active calls).

### wxcadm vs wxc_sdk
- The opening section clearly states XSI is wxcadm-unique. No comparison table needed since wxc_sdk has zero XSI support.

### Bugs Documented
1. `recording()` method -- `"resume"` maps to `PauseRecording` due to duplicate elif. Documented in both the method section AND the Gotchas section. Tagged `<!-- NEEDS VERIFICATION -->`.

Note: Gotcha #10 says "The `'pause'` action case is unreachable" while the method section says "`action='resume'` maps to `PauseRecording`". These describe the same bug differently. The Gotchas phrasing is slightly misleading -- it's the "pause" *case* that's unreachable, not the "resume" case. Consider aligning the descriptions.

### Cross-references
- Class Reference Summary table at the end is an excellent quick-reference.

### Formatting
- Strong structure with Architecture Overview, Setup, Actions, Events, Use Cases, Gotchas. Code examples for 6 use cases. Consistent throughout.

---

## 7. wxcadm-routing.md

### Accuracy
- **CallRouting**: Entry point with `trunks`, `route_groups`, `route_lists`, `dial_plans` properties. `test()` method with Person/Trunk originator.
- **Trunks**: `Trunks.get()`, `Trunks.add_trunk()` with REGISTERING vs CERTIFICATE_BASED params. `Trunk` dataclass with lazy-loaded detail fields.
- **RouteGroups**: `RouteGroups.get()`, `RouteGroup.trunks` property, `RouteGroup.add_trunk()` with priority options (`'next'`, `'with_last'`, int).
- **RouteLists**: `RouteLists.create()`, `RouteLists.get()`. `RouteList` with `__post_init__` resolution.
- **DialPlans**: No `get()` method on collection -- correctly noted with manual iteration workaround. `DialPlan.patterns`, `add_pattern()`, `delete_pattern()`.
- **TranslationPatternList**: Org or location scope, full CRUD. `get()` with AND logic across multiple criteria.
- **LocationPSTN**: Provider get/set. `set_provider()` accepting multiple types.
- **CDR**: Full `CallDetailRecords -> Call -> CallLeg -> LegPart` hierarchy. `LegPart` attribute table mapping raw CSV field names.
- **Reports**: `ReportList` with templates, `cdr_report()` shortcut, `Report` with status/download.
- **Jobs**: All three types (Number Management, User Move, Rebuild Phones) documented with create/completed/success patterns.
- **Webhooks**: Full CRUD with activate/deactivate.

### Gaps
- `CallRouting` properties are noted as "freshly-initialized collection -- no caching" -- important behavioral note, correctly documented.
- `RouteLists` delete noted as "TODO in source" -- good.
- `DialPlans` has no `get()` method -- correctly noted.
- CDR module is documented as a post-processing class, not a fetcher -- correctly explained.

### wxcadm vs wxc_sdk
- Comprehensive comparison table covering all 12 feature areas. `<!-- NEEDS VERIFICATION -->` tag on the overall comparison -- appropriate.
- Key architectural differences section highlighting UserList pattern, lazy loading, CDR processing uniqueness, and job validation pattern.

### Bugs Documented
1. `RouteList.__post_init__` calls `get_route_group()` but `RouteGroups` only has `get()`. Tagged `<!-- NEEDS VERIFICATION -->`.
2. `RouteList.numbers` property calls `response.json()` instead of using parsed response. Tagged `<!-- NEEDS VERIFICATION -->`.
3. `RebuildPhonesJob` lacks `success` property unlike other job types. Tagged `<!-- NEEDS VERIFICATION -->`.

### Cross-references
- API Endpoint Summary table at the end covers all module endpoints.

### Formatting
- Numbered section headings (unique among the 8 docs). Consistent tables and code blocks. Table of Contents with numbered sections.

---

## 8. wxcadm-advanced.md

### Accuracy
- **RedSky**: Architecture (Building > Location), standalone auth, `add_building()` from Webex Location, all 4 network discovery types (MAC, LLDP, BSSID, IP Range), HELD devices, users. Comprehensive.
- **Meraki**: Tag-based convention (`911-`), `attach_redsky()`, `redsky_audit()` with simulate mode, audit results attributes, device type hierarchy.
- **CP-API**: VM PIN management (with race condition warning), workspace caller ID, MOH upload, AA greetings, deprecated numbers. Warning about CP-API scope requirements.
- **Applications**: `WebexApplications`, Service App lifecycle (create -> authorize -> get_token -> refresh). `WebexApplication` dataclass fields.
- **Wholesale**: Standalone entry point, customers/locations, subscriber provisioning.
- **Bifrost**: Minimal but honest documentation. Notes it's 52 lines and may be expanded.

### Gaps
- **RedSky**: `RedSky.get_all_locations()` returns corporate vs personal locations -- documented.
- **Meraki**: Building determination logic (normalized address then street-only fallback) documented.
- **CP-API**: `get_workspace_calling_location()` documented but brief.
- **Wholesale**: `WholesaleCustomer.add_subscriber()` signature is complete but example usage is not shown.
- **Bifrost**: `bifrost_config` contents are unknown -- tagged `<!-- NEEDS VERIFICATION -->`.

### wxcadm vs wxc_sdk
- Opening statement: "These modules are unique to wxcadm -- none of them have equivalents in wxc_sdk." Summary table at the end reinforces this.

### Bugs Documented
1. `CPAPI.reset_vm_pin` race condition with temporary global PIN. Tagged `<!-- NEEDS VERIFICATION -->`.

### Cross-references
- Good cross-referencing within the doc (RedSky -> Meraki, CP-API -> Org methods).

### Formatting
- Consistent with the other docs. Good use of tables for attributes and audit results.

---

## NEEDS VERIFICATION Tags -- Complete Inventory

| # | Doc | Location | Tag Content |
|---|-----|----------|-------------|
| 1 | core | Line 282 | `get_recordings()` kwargs |
| 2 | core | Line 622 | CPAPI support in wxcadm |
| 3 | core | Line 630-631 | "When to use wxcadm" CPAPI bullet |
| 4 | person | Line 226 | `role_names()` return-inside-loop bug |
| 5 | person | Line 1141 | `SnrNumber.set_do_not_forward_calls` copy-paste bug |
| 6 | person | Line 1164 | wxc_sdk voicemail greeting upload equivalent |
| 7 | person | Line 1169 | wxc_sdk ECBN equivalent |
| 8 | person | Line 1170 | wxc_sdk SNR equivalent |
| 9 | person | Line 1171 | wxc_sdk Application Line Assignments equivalent |
| 10 | person | Line 1174 | wxc_sdk GroupApi equivalent |
| 11 | person | Line 1175 | wxc_sdk Voice Messages equivalent |
| 12 | locations | Line 638 | `update_event` truncated API URL |
| 13 | locations | Line 691 | VoicePortal RealtimeClass auto-push behavior |
| 14 | locations | Line 751 | PagingGroup access pattern unclear |
| 15 | locations | Line 805 | `org.voicemail_groups` attribute name |
| 16 | locations | Line 894 | wxc_sdk location delete support |
| 17 | locations | Line 901 | wxc_sdk `enable_for_calling()` |
| 18 | locations | Line 915 | wxc_sdk schedule management comparison |
| 19 | features | Line 238 | `CallQueue.add_agent` -- `pass` in source |
| 20 | features | Line 276 | `HuntGroupList.get` -- `.uppper()` typo |
| 21 | features | Line 384 | `PickupGroupList` -- no refresh/create/delete |
| 22 | features | Line 527 | `Playlist.__getattr__` -- `"fv1/..."` URL bug |
| 23 | features | Line 608 | `OrgRecordingVendorSelection.set_failure_behavior` not implemented |
| 24 | features | Line 684 | `ComplianceAnnouncementSettings.push` double-slash |
| 25 | features | Lines 773-782 | wxc_sdk comparison (9 separate verification notes) |
| 26 | devices-workspaces | Line 418 | DECT access pattern (org/location accessor wiring) |
| 27 | devices-workspaces | Line 985 | `VirtualLine.get_call_recording()` -- passes 'get' as URL |
| 28 | devices-workspaces | Line 996 | `VirtualLine.delete()` returns False on success |
| 29 | devices-workspaces | Line 1174 | wxc_sdk DECT network create equivalent |
| 30 | devices-workspaces | Line 1175 | wxc_sdk virtual line CRUD equivalent |
| 31 | xsi-realtime | Line 377 | `recording()` resume/pause bug still present |
| 32 | xsi-realtime | Line 499 | Full list of event packages |
| 33 | xsi-realtime | Line 538 | Complete event type list |
| 34 | xsi-realtime | Line 577 | Exact payload field names |
| 35 | xsi-realtime | Line 722 | Call Queue call control subset |
| 36 | xsi-realtime | Line 924 | `recording()` pause bug (duplicate of #31) |
| 37 | routing | Line 275 | `RouteList.__post_init__` calls `get_route_group()` |
| 38 | routing | Line 286 | `RouteList.numbers` calls `response.json()` |
| 39 | routing | Line 1074 | `RebuildPhonesJob` lacks `success` property |
| 40 | routing | Line 1197 | wxc_sdk comparison accuracy |
| 41 | advanced | Line 529 | `CPAPI.reset_vm_pin` race condition |
| 42 | advanced | Line 583 | `CPAPI.get_numbers()` deprecated |
| 43 | advanced | Line 640 | Service Apps "Early Field Trial" status |
| 44 | advanced | Line 784 | Bifrost `bifrost_config` contents |

**Total: 44 NEEDS VERIFICATION tags** (42 unique, 2 duplicates: #31/#36).

---

## Cross-Cutting Issues

### 1. `get_xsi` Parameter Discrepancy
`wxcadm-xsi-realtime.md` shows `wxcadm.Webex(access_token, get_xsi=True)` but `wxcadm-core.md` does not list `get_xsi` in the `Webex` constructor signature. **One doc is wrong.** Verify against source and fix.

### 2. `Org.calls` vs `person.xsi.calls`
`wxcadm-core.md` lists `calls: Calls` as a non-cached Org property. `wxcadm-xsi-realtime.md` documents `person.xsi.calls` for per-user active calls. The Org-level `Calls` class is not documented anywhere. Either document it or explain the relationship.

### 3. Cross-references to wxc_sdk Docs
Every wxcadm doc has a "wxcadm vs wxc_sdk" comparison section, but none link to the corresponding wxc_sdk reference docs in this same `/docs/reference/` directory (e.g., `wxc-sdk-patterns.md`, `person-call-settings-handling.md`, etc.). Adding explicit links would help readers navigate between the two libraries' documentation.

### 4. Formatting Consistency
- **Section numbering**: `wxcadm-routing.md` uses numbered top-level sections (1-7). All other docs use unnumbered headings. Minor inconsistency.
- **Table of Contents**: All 8 docs have a ToC. Good.
- **Bug note style**: All use `<!-- NEEDS VERIFICATION -->` HTML comments with inline context. Consistent.
- **Code example density**: XSI doc has 6 use cases with full code. Features doc has fewer examples. Advanced doc has good examples for RedSky/Meraki but fewer for CP-API/Wholesale.

### 5. Missing Call Settings
The person doc covers 19 out of ~34 Webex Calling person settings. The ones missing (Call Waiting, Sequential Ring, Simultaneous Ring, Priority Alert, Anonymous Call Rejection via REST, COLR, CLIR, etc.) are likely not implemented in wxcadm. The doc should explicitly state: "wxcadm covers N settings; the remaining settings are available only through wxc_sdk or the Webex REST API directly."

---

## Summary Scorecard

| Doc | Accuracy | Gaps | wxcadm vs wxc_sdk | Bugs Flagged | Cross-refs | Formatting |
|-----|----------|------|-------------------|-------------|------------|------------|
| core | Good | `get_xsi` param missing | Good | 1 | None to wxc_sdk docs | Good |
| person | Good | Note missing settings count | Good, many NEEDS VERIFICATION | 2 | None to wxc_sdk docs | Good |
| locations | Good | recording_vendor cross-ref | Good | 3 | Internal only | Good |
| features | Good | No CQ supervisor detail | Good, heavy NEEDS VERIFICATION | 6 | API URL table | Good |
| devices-workspaces | Good | DeviceList constructor | Good | 2 | Webex Dev docs | Good |
| xsi-realtime | Good | Event packages incomplete | N/A (unique to wxcadm) | 1 (duped) | Class summary table | Good |
| routing | Good | Minimal gaps | Good | 3 | API endpoint table | Minor numbering inconsistency |
| advanced | Good | Bifrost minimal | N/A (unique to wxcadm) | 1 | Internal cross-refs | Good |

### Priority Fixes
1. **Resolve `get_xsi` discrepancy** between core and XSI docs (verify against source)
2. **Document `Org.calls`** or remove from core doc's property table
3. **Add explicit wxc_sdk doc cross-references** to each comparison section
4. **Add "not covered" note** to person doc listing which settings wxcadm does not implement
5. **Align recording() bug description** between XSI method section and Gotchas #10

### Overall Assessment
The 8 docs are thorough, well-structured, and honest about limitations. The `<!-- NEEDS VERIFICATION -->` tagging is disciplined -- bugs and uncertainties are clearly marked rather than hidden. The wxcadm vs wxc_sdk comparisons are present in every doc and provide practical "when to use which" guidance. The main improvements needed are cross-references between the wxcadm and wxc_sdk doc sets, resolving the `get_xsi` discrepancy, and explicitly noting which person call settings are out of wxcadm's scope.
