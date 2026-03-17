# Coverage Audit: 29 Reference Docs vs. Webex Calling API Surface

**Audited:** 2026-03-17
**Doc count:** 29 (21 wxc_sdk + 8 wxcadm)
**Verdict:** No major gaps. All wxc_sdk top-level APIs, telephony sub-APIs, person_settings sub-APIs, and wxcadm-unique features are covered. Two areas are intentionally deferred (meetings, messaging). A handful of minor notes below.

---

## 1. wxc_sdk Top-Level APIs

| API | Covered In (wxc_sdk) | Also In (wxcadm) | Status |
|-----|----------------------|-------------------|--------|
| **people** | `provisioning.md` | `wxcadm-person.md` | COVERED (dual) |
| **licenses** | `provisioning.md` | `wxcadm-core.md` (Org.licenses) | COVERED (dual) |
| **locations** | `provisioning.md` | `wxcadm-locations.md` | COVERED (dual) |
| **organizations** | `provisioning.md` | `wxcadm-core.md` (Org class) | COVERED (dual) |
| **telephony** | Multiple (see Section 2 below) | Multiple (see Section 2) | COVERED |
| **person_settings** | 4 dedicated docs (handling, media, permissions, behavior) | `wxcadm-person.md` | COVERED (dual) |
| **devices** | `devices-core.md` | `wxcadm-devices-workspaces.md` | COVERED (dual) |
| **device_configurations** | `devices-core.md` (DeviceConfigurationsApi) | -- | COVERED |
| **workspaces** | `devices-workspaces.md` | `wxcadm-devices-workspaces.md` | COVERED (dual) |
| **workspace_settings** | `devices-workspaces.md` | `wxcadm-devices-workspaces.md` | COVERED (dual) |
| **workspace_locations** | `devices-workspaces.md` (legacy WorkspaceLocationApi) | -- | COVERED |
| **workspace_personalization** | `devices-workspaces.md` | -- | COVERED |
| **webhook** | `webhooks-events.md` | `wxcadm-routing.md` (Webhooks class) | COVERED (dual) |
| **cdr** | `reporting-analytics.md` | `wxcadm-routing.md` (CDR class) | COVERED (dual) |
| **reports** | `reporting-analytics.md` | `wxcadm-routing.md` (Reports class) | COVERED (dual) |
| **meetings** | -- | -- | DEFERRED to `docs/later/webex-meetings.md` |

---

## 2. wxc_sdk telephony Sub-APIs

| Sub-API | Covered In (wxc_sdk) | Also In (wxcadm) | Status |
|---------|----------------------|-------------------|--------|
| **auto_attendant** | `call-features-major.md` | `wxcadm-features.md` | COVERED (dual) |
| **callqueue** | `call-features-major.md` | `wxcadm-features.md` | COVERED (dual) |
| **huntgroup** | `call-features-major.md` | `wxcadm-features.md` | COVERED (dual) |
| **paging** | `call-features-additional.md` | `wxcadm-locations.md` (PagingGroup) | COVERED (dual) |
| **callpark** | `call-features-additional.md` | -- | COVERED |
| **callpark_extension** | `call-features-additional.md` | `wxcadm-locations.md` (CallParkExtension) | COVERED (dual) |
| **callpickup** | `call-features-additional.md` | `wxcadm-features.md` (Pickup Group) | COVERED (dual) |
| **voicemail_groups** | `call-features-additional.md` | `wxcadm-locations.md` (VoicemailGroup) | COVERED (dual) |
| **cx_essentials** | `call-features-additional.md` | -- | COVERED |
| **dial_plan** | `call-routing.md` | `wxcadm-routing.md` | COVERED (dual) |
| **trunk** | `call-routing.md` | `wxcadm-routing.md` | COVERED (dual) |
| **route_group** | `call-routing.md` | `wxcadm-routing.md` | COVERED (dual) |
| **route_list** | `call-routing.md` | `wxcadm-routing.md` | COVERED (dual) |
| **translation_pattern** | `call-routing.md` | `wxcadm-routing.md` | COVERED (dual) |
| **calls** | `call-control.md` | `wxcadm-xsi-realtime.md` (XSI call control) | COVERED (dual, different mechanisms) |
| **call_recording** | `location-call-settings-advanced.md` | `wxcadm-features.md` (Recording) | COVERED (dual) |
| **caller_reputation** | `location-call-settings-advanced.md` | -- | COVERED |
| **conference** | `location-call-settings-advanced.md` | -- | COVERED |
| **dect_devices** | `devices-dect.md` | `wxcadm-devices-workspaces.md` (DECT Networks) | COVERED (dual) |
| **devices (telephony)** | `devices-core.md` (TelephonyDevicesApi) | `wxcadm-devices-workspaces.md` | COVERED (dual) |
| **emergency_address** | `emergency-services.md` | -- | COVERED |
| **emergency_services** | `emergency-services.md`, `location-call-settings-core.md` | `wxcadm-locations.md` | COVERED (dual) |
| **guest_calling** | `location-call-settings-advanced.md` | -- | COVERED |
| **hotdesk** | `devices-dect.md` | -- | COVERED |
| **hotdesking_voiceportal** | `location-call-settings-advanced.md` | -- | COVERED |
| **location** | `location-call-settings-core.md` | `wxcadm-locations.md` | COVERED (dual) |
| **operating_modes** | `location-call-settings-advanced.md` | -- | COVERED |
| **org_access_codes** | `location-call-settings-media.md` | -- | COVERED |
| **organisation_vm** | `location-call-settings-core.md` | -- | COVERED |
| **pnc** (Private Network Connect) | `call-routing.md` | -- | COVERED |
| **prem_pstn** (Premises PSTN) | `call-routing.md` | `wxcadm-routing.md` (PSTN) | COVERED (dual) |
| **pstn** | `call-routing.md` | `wxcadm-routing.md` | COVERED (dual) |
| **supervisor** | `location-call-settings-advanced.md` | -- | COVERED |
| **virtual_extensions** | `virtual-lines.md` | -- | COVERED |
| **virtual_line** | `virtual-lines.md` | `wxcadm-devices-workspaces.md` | COVERED (dual) |
| **vm_rules** | `location-call-settings-core.md` | -- | COVERED |
| **voice_messaging** | `location-call-settings-core.md` | -- | COVERED |
| **voiceportal** | `location-call-settings-core.md` | `wxcadm-locations.md` | COVERED (dual) |
| **announcements_repo** | `location-call-settings-media.md` | `wxcadm-features.md` (Announcements) | COVERED (dual) |
| **playlists** | `location-call-settings-media.md` | `wxcadm-features.md` (Playlists) | COVERED (dual) |
| **forwarding (shared)** | `call-features-major.md` (Shared Forwarding API), `location-call-settings-advanced.md` | -- | COVERED |
| **access_codes** | `location-call-settings-media.md` | -- | COVERED |

---

## 3. wxc_sdk person_settings Sub-APIs

| Sub-API | Covered In | Status |
|---------|-----------|--------|
| **forwarding** | `person-call-settings-handling.md` | COVERED |
| **voicemail** | `person-call-settings-media.md` | COVERED |
| **dnd** | `person-call-settings-handling.md` | COVERED |
| **caller_id** | `person-call-settings-media.md` | COVERED |
| **agent_caller_id** | `person-call-settings-media.md` | COVERED |
| **anon_calls** | `person-call-settings-media.md` | COVERED |
| **barge** | `person-call-settings-media.md` | COVERED |
| **call_intercept** | `person-call-settings-media.md` | COVERED |
| **call_recording** | `person-call-settings-media.md` | COVERED |
| **call_waiting** | `person-call-settings-handling.md` | COVERED |
| **privacy** | `person-call-settings-media.md` | COVERED |
| **push_to_talk** | `person-call-settings-media.md` | COVERED |
| **monitoring** | `person-call-settings-media.md` | COVERED |
| **permissions_in** | `person-call-settings-permissions.md` | COVERED |
| **permissions_out** | `person-call-settings-permissions.md` | COVERED |
| **feature_access** | `person-call-settings-permissions.md` | COVERED |
| **executive** | `person-call-settings-permissions.md` | COVERED |
| **exec_assistant** | `person-call-settings-permissions.md` | COVERED |
| **calling_behavior** | `person-call-settings-behavior.md` | COVERED |
| **appservices** | `person-call-settings-behavior.md` (App Services) | COVERED |
| **app_shared_line** | `person-call-settings-behavior.md` | COVERED |
| **callbridge** | `person-call-settings-behavior.md` (Call Bridge) | COVERED |
| **hoteling** | `person-call-settings-behavior.md` | COVERED |
| **receptionist** | `person-call-settings-behavior.md` (Receptionist Client) | COVERED |
| **numbers** | `person-call-settings-behavior.md` | COVERED |
| **available_numbers** | `person-call-settings-behavior.md` | COVERED |
| **preferred_answer** | `person-call-settings-behavior.md` (Preferred Answer Endpoint) | COVERED |
| **msteams** | `person-call-settings-behavior.md` (MS Teams) | COVERED |
| **mode_management** | `person-call-settings-behavior.md` | COVERED |
| **personal_assistant** | `person-call-settings-behavior.md` | COVERED |
| **ecbn** | `person-call-settings-behavior.md` (Emergency Callback Number) | COVERED |
| **call_policy** | `person-call-settings-permissions.md` | COVERED |
| **moh** (Music on Hold) | `person-call-settings-media.md` | COVERED |
| **sim_ring** | `person-call-settings-handling.md` | COVERED |
| **sequential_ring** | `person-call-settings-handling.md` | COVERED |
| **single_number_reach** | `person-call-settings-handling.md` | COVERED |
| **selective_accept** | `person-call-settings-handling.md` | COVERED |
| **selective_forward** | `person-call-settings-handling.md` | COVERED |
| **selective_reject** | `person-call-settings-handling.md` | COVERED |
| **priority_alert** | `person-call-settings-handling.md` | COVERED |

---

## 4. wxcadm-Unique Features

| Feature | Covered In | Status |
|---------|-----------|--------|
| **XSI Events (real-time call monitoring)** | `wxcadm-xsi-realtime.md` | COVERED |
| **XSI Actions (programmatic call control)** | `wxcadm-xsi-realtime.md` | COVERED |
| **CP-API (Control Hub internal API)** | `wxcadm-advanced.md` | COVERED |
| **RedSky E911** | `wxcadm-advanced.md` | COVERED |
| **Meraki integration** | `wxcadm-advanced.md` | COVERED |
| **Wholesale provisioning** | `wxcadm-advanced.md` | COVERED |
| **Bifrost internal API** | `wxcadm-advanced.md` | COVERED |
| **Jobs (number moves, user moves, phone rebuilds)** | `wxcadm-routing.md` | COVERED |
| **Applications / Service Apps** | `wxcadm-advanced.md` | COVERED |

---

## 5. Cross-Cutting / Infrastructure

| Area | Covered In | Status |
|------|-----------|--------|
| **Authentication (all methods)** | `authentication.md` | COVERED |
| **wxc_sdk patterns & setup** | `wxc-sdk-patterns.md` | COVERED |
| **wxcadm object model & setup** | `wxcadm-core.md` | COVERED |
| **Schedules (business hours, holidays)** | `location-call-settings-media.md`, `wxcadm-locations.md` | COVERED |
| **Phone number management** | `call-routing.md`, `wxcadm-devices-workspaces.md` | COVERED |

---

## 6. Intentionally Deferred (Not Gaps)

These items are explicitly out of scope for the calling-focused playbook and parked in `docs/later/`:

| Area | Parked In | Notes |
|------|-----------|-------|
| **Meetings API** | `docs/later/webex-meetings.md` | Scheduling, invitees, recordings |
| **Messaging API** | `docs/later/webex-messaging.md` | Rooms, messages, teams, memberships |
| **Bots & Webhooks (non-calling)** | `docs/later/webex-bots-webhooks.md` | Bot lifecycle, non-telephony webhooks |

---

## 7. Duplicate Coverage Analysis

The following API areas are covered in BOTH wxc_sdk and wxcadm docs. This is **intentional** -- the two libraries have different APIs, object models, and capabilities for the same underlying Webex Calling features. Each wxcadm doc includes a "wxcadm vs wxc_sdk" comparison section.

| Area | wxc_sdk Doc | wxcadm Doc | Intentional? |
|------|------------|------------|:------------:|
| People/Users | `provisioning.md` | `wxcadm-person.md` | Yes |
| Locations | `provisioning.md` | `wxcadm-locations.md` | Yes |
| Auto Attendants | `call-features-major.md` | `wxcadm-features.md` | Yes |
| Call Queues | `call-features-major.md` | `wxcadm-features.md` | Yes |
| Hunt Groups | `call-features-major.md` | `wxcadm-features.md` | Yes |
| Devices / DECT | `devices-core.md`, `devices-dect.md` | `wxcadm-devices-workspaces.md` | Yes |
| Workspaces | `devices-workspaces.md` | `wxcadm-devices-workspaces.md` | Yes |
| Virtual Lines | `virtual-lines.md` | `wxcadm-devices-workspaces.md` | Yes |
| Call Routing (all) | `call-routing.md` | `wxcadm-routing.md` | Yes |
| PSTN | `call-routing.md` | `wxcadm-routing.md` | Yes |
| Webhooks | `webhooks-events.md` | `wxcadm-routing.md` | Yes |
| CDR / Reports | `reporting-analytics.md` | `wxcadm-routing.md` | Yes |
| Announcements | `location-call-settings-media.md` | `wxcadm-features.md` | Yes |
| Call Recording | `location-call-settings-advanced.md` | `wxcadm-features.md` | Yes |
| Emergency Services | `emergency-services.md` | `wxcadm-locations.md` | Yes |
| Call Control | `call-control.md` (REST API) | `wxcadm-xsi-realtime.md` (XSI) | Yes (different mechanisms) |
| Person Call Settings | 4 dedicated docs | `wxcadm-person.md` (34 methods) | Yes |

No **unintentional** duplicate coverage was found. Every dual-coverage case exists because wxc_sdk and wxcadm expose the same underlying API through different interfaces.

---

## 8. Gaps Found

### True Gaps: NONE

Every API area listed in the audit scope is covered by at least one reference doc.

### Minor Notes (not gaps, but worth flagging):

1. **`wxc_sdk.telephony.callpark`** -- Call Park is covered in `call-features-additional.md`, but the wxcadm side has no dedicated Call Park module. wxcadm covers Call Park Extension (via `wxcadm-locations.md`) but not the group-level Call Park CRUD. This is a wxcadm library limitation, not a doc gap.

2. **`wxc_sdk.telephony.cx_essentials`** -- Covered only in `call-features-additional.md` (wxc_sdk side). wxcadm has no CX Essentials module. This is a wxcadm library limitation.

3. **`wxc_sdk.telephony.caller_reputation`** and **`wxc_sdk.telephony.conference`** -- Only covered on the wxc_sdk side (`location-call-settings-advanced.md`). wxcadm has no equivalent modules. Library limitation, not doc gap.

4. **Jobs API** -- Only covered on the wxcadm side (`wxcadm-routing.md`). wxc_sdk does have a Jobs API (for number management, user moves, etc.) but it is not documented in its own wxc_sdk reference doc. The functionality is mentioned in `wxc-sdk-patterns.md` examples but not given dedicated coverage. **This is the closest thing to an actual gap** -- consider adding a Jobs section to an existing wxc_sdk doc (e.g., `provisioning.md` or `reporting-analytics.md`).

5. **Schedules** -- Covered in `location-call-settings-media.md` (wxc_sdk) and `wxcadm-locations.md` (wxcadm), but there is no standalone "Schedules" doc. This is fine given that schedules are location-scoped and covered within location docs.

---

## 9. Overall Assessment

**Coverage: COMPLETE** for the Webex Calling API surface.

- All 15 wxc_sdk top-level API modules: 14 covered, 1 intentionally deferred (meetings)
- All 40+ wxc_sdk telephony sub-APIs: fully covered
- All 39 wxc_sdk person_settings sub-APIs: fully covered
- All 9 wxcadm-unique features: fully covered
- All intentional dual coverage (wxc_sdk + wxcadm) is properly marked

**One recommendation:** Add wxc_sdk Jobs API coverage to an existing doc (the wxcadm side already has it in `wxcadm-routing.md`, but the wxc_sdk equivalent is undocumented).
