# API Audit: Person & Workspace Call Settings — CUCM Migration Coverage Map

**Date:** 2026-04-10
**Source:** OpenAPI spec `specs/webex-cloud-calling.json` (144 person endpoints + 81 workspace endpoints + 149 /people/me endpoints)
**Cross-referenced against:** call_settings_mapper.py, voicemail_mapper.py, call_forwarding_mapper.py, monitoring_mapper.py, snr_mapper.py, e911_mapper.py, moh_mapper.py, css_mapper.py, workspace_mapper.py, handlers.py (31 handlers in HANDLER_REGISTRY)

---

## Summary

| Category | Total Settings | Covered | Partial | Gap | User-Only (no admin API) |
|----------|---------------|---------|---------|-----|--------------------------|
| Call Handling | 14 | 5 | 1 | 8 | 3 |
| Voicemail & Media | 12 | 4 | 2 | 6 | 0 |
| Permissions | 8 | 2 | 0 | 6 | 0 |
| Behavior & Devices | 16 | 3 | 1 | 12 | 0 |
| Workspace-Specific | 14 | 1 | 0 | 13 | 0 |
| **TOTAL** | **64** | **15** | **4** | **45** | **3** |

**Coverage rate: 23% fully covered, 30% including partial.**

---

## Category 1: Call Handling

Settings that control how incoming calls are routed, filtered, and alerted.

| # | Setting Name | Webex API Path (Admin) | CUCM Equivalent | Discovered? | Mapped? | Configured? | Gap? | Priority |
|---|-------------|----------------------|-----------------|-------------|---------|-------------|------|----------|
| 1 | **Call Forwarding (CFA/CFB/CFNA)** | `PUT /people/{id}/features/callForwarding` | Per-line CFA, CFB, CFNA destinations | Yes | Yes (call_forwarding_mapper) | Yes (handle_call_forwarding_configure) | No | -- |
| 2 | **Call Forwarding (Business Continuity)** | `PUT /people/{id}/features/callForwarding` (businessContinuity sub-field) | No direct equivalent (CUCM uses SRSTs) | No | No | Hardcoded `enabled: false` | Partial | Low |
| 3 | **Do Not Disturb** | `PUT /people/{id}/features/doNotDisturb` | Phone-level dndStatus + dndOption | Yes | Yes (call_settings_mapper) | Yes (handle_user_configure_settings) | No | -- |
| 4 | **Call Waiting** | `PUT /people/{id}/features/callWaiting` | Per-line callWaiting | Yes | Yes (call_settings_mapper) | Yes (handle_user_configure_settings) | No | -- |
| 5 | **Single Number Reach** | `PUT /telephony/config/people/{id}/singleNumberReach` + `POST .../numbers` | Remote Destinations + Mobile Connect | Yes | Yes (snr_mapper) | Yes (handle_snr_configure) | No | -- |
| 6 | **Simultaneous Ring** | User-only: `/people/me/settings/simultaneousRing` | No direct CUCM equivalent (SNR is closest) | N/A | No | No | **YES** | Low |
| 7 | **Sequential Ring** | User-only: `/people/me/settings/sequentialRing` | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 8 | **Selective Call Accept** | `PUT /telephony/config/people/{id}/selectiveAccept` + criteria CRUD | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 9 | **Selective Call Forward** | `PUT /telephony/config/people/{id}/selectiveForward` + criteria CRUD | No direct CUCM equivalent (uses Time-of-Day routing via CSS) | N/A | No | No | **YES** | Low |
| 10 | **Selective Call Reject** | `PUT /telephony/config/people/{id}/selectiveReject` + criteria CRUD | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 11 | **Priority Alert** | User-only: `/people/me/settings/priorityAlert` | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 12 | **Call Notify** | User-only: `/people/me/settings/callNotify` + criteria CRUD | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 13 | **Person Schedules** | `POST /people/{id}/features/schedules` + events CRUD | CUCM Time Schedules (extracted but used for features, not per-user) | Partial | No | No | **YES** | Medium |
| 14 | **Call Intercept** | `PUT /people/{id}/features/intercept` + greeting upload | CUCM Device/Line overrides, no exact equivalent | No | No | No | **YES** | Medium |

### Analysis — Call Handling

**Fully covered (5):** Call Forwarding, DND, Call Waiting, Single Number Reach are discovered from CUCM, mapped, and configured in Webex.

**Partial (1):** Business Continuity forwarding is hardcoded to `false` in the handler. CUCM uses SRST for survivability which is a different architecture. Acceptable.

**Gaps (8):** Simultaneous Ring, Sequential Ring, Selective rules (accept/forward/reject), Priority Alert, Call Notify, and Person Schedules have no CUCM equivalent or no admin API path. Call Intercept has a CUCM-adjacent concept but no mapper.

**Call Intercept is the highest-priority gap** — CUCM admins use it for intercepting calls to suspended/terminated users. A mapper could detect CUCM device overrides that serve a similar purpose.

---

## Category 2: Voicemail & Media

Settings covering voicemail configuration, caller ID, recording, MOH, and related media.

| # | Setting Name | Webex API Path (Admin) | CUCM Equivalent | Discovered? | Mapped? | Configured? | Gap? | Priority |
|---|-------------|----------------------|-----------------|-------------|---------|-------------|------|----------|
| 15 | **Voicemail Settings** | `PUT /people/{id}/features/voicemail` (classic) or `PUT /telephony/config/people/{id}/voicemail` | Unity Connection profiles + per-user VM settings | Yes | Yes (voicemail_mapper) | Yes (handle_user_configure_voicemail) | No | -- |
| 16 | **Voicemail PIN Reset** | `POST /people/{id}/features/voicemail/actions/resetPin/invoke` | Unity Connection PIN policy | No | No | No | **YES** | Medium |
| 17 | **Voicemail Passcode** | `PUT /telephony/config/people/{id}/voicemail/passcode` | Unity Connection credential policy | No | No | No | **YES** | Medium |
| 18 | **Voicemail Busy Greeting Upload** | `POST /people/{id}/features/voicemail/actions/uploadBusyGreeting/invoke` | Unity Connection custom greetings | Detected (MISSING_DATA decision) | No (audio not extractable) | No | Partial — correctly flagged | Low |
| 19 | **Voicemail No-Answer Greeting Upload** | `POST /people/{id}/features/voicemail/actions/uploadNoAnswerGreeting/invoke` | Unity Connection custom greetings | Detected (MISSING_DATA decision) | No (audio not extractable) | No | Partial — correctly flagged | Low |
| 20 | **Caller ID** | `PUT /people/{id}/features/callerId` | Phone callerIdBlock + external CPN settings | Yes | Yes (call_settings_mapper) | Yes (handle_user_configure_settings) | No | -- |
| 21 | **Agent Caller ID** | `GET/PUT /telephony/config/people/{id}/agent/callerId` | CUCM Enterprise param + per-line CLID settings | No | No | No | **YES** | Medium |
| 22 | **Call Recording** | `PUT /people/{id}/features/callRecording` | Phone builtInBridgeStatus | Yes | Yes (call_settings_mapper) | Yes (handle_user_configure_settings) | No | -- |
| 23 | **Music on Hold (Person-level)** | `PUT /telephony/config/people/{id}/musicOnHold` | Device Pool MOH Audio Source ref | Yes (moh_mapper) | Yes (CanonicalMusicOnHold) | No handler for per-person MOH | **YES** | Medium |
| 24 | **Call Captions** | `GET/PUT /telephony/config/people/{id}/callCaptions` | No CUCM equivalent (new Webex feature) | N/A | No | No | **YES** | Low |
| 25 | **Anonymous Call Rejection** | Workspace-only admin path; person uses `/people/me/settings/anonymousCallReject` | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 26 | **Call Bridge (Warning Tone)** | `GET/PUT /telephony/config/people/{id}/features/callBridge` | No direct CUCM equivalent | N/A | No | No | **YES** | Low |

### Analysis — Voicemail & Media

**Fully covered (4):** Voicemail Settings, Caller ID, Call Recording all have full discover-map-configure chains.

**Partial (2):** Greeting uploads are correctly flagged as MISSING_DATA decisions (audio files can't be extracted from Unity). This is the right approach.

**Gaps (6):** VM PIN Reset, VM Passcode, Agent Caller ID, Person-level MOH, Call Captions, Anonymous Call Rejection, and Call Bridge have no mapper or handler.

**Person-level MOH is notable:** the moh_mapper produces CanonicalMusicOnHold objects (location-level), but there's no handler to set per-person MOH source via `PUT /telephony/config/people/{id}/musicOnHold`. CUCM assigns MOH at the device pool level which maps to location-level in Webex, so this is usually acceptable. Per-user overrides are rare.

---

## Category 3: Permissions

Settings controlling incoming/outgoing call permissions, access codes, and feature access.

| # | Setting Name | Webex API Path (Admin) | CUCM Equivalent | Discovered? | Mapped? | Configured? | Gap? | Priority |
|---|-------------|----------------------|-----------------|-------------|---------|-------------|------|----------|
| 27 | **Outgoing Permissions** | `PUT /people/{id}/features/outgoingPermission` | CSS-based calling restrictions (CSS → partition → route pattern) | Yes | Yes (css_mapper → CanonicalCallingPermission) | Yes (handle_calling_permission_assign) | No | -- |
| 28 | **Incoming Permissions** | `PUT /people/{id}/features/incomingPermission` | No direct CUCM equivalent (handled by CSS/partition filtering) | Partial | No dedicated mapper | No | **YES** | Medium |
| 29 | **Outgoing Access Codes** | `POST/PUT/DELETE /telephony/config/people/{id}/outgoingPermission/accessCodes` | CUCM FAC (Forced Authorization Codes) | No | No | No | **YES** | Medium |
| 30 | **Outgoing Transfer Numbers** | `GET/PUT /telephony/config/people/{id}/outgoingPermission/autoTransferNumbers` | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 31 | **Outgoing Digit Patterns** | `CRUD /telephony/config/people/{id}/outgoingPermission/digitPatterns` | CSS partition blocking patterns | Partial (css_mapper detects) | No per-user output | No | **YES** | Medium |
| 32 | **Call Policies** | `GET/PUT /telephony/config/workspaces/{id}/callPolicies` (workspace); user via `/me/settings/callPolicies` | CUCM Enterprise params + Phone NTP refs | No | No | No | **YES** | Low |
| 33 | **Executive/Assistant** | `GET/PUT /telephony/config/people/{id}/executive/*` (8+ endpoints: alert, assignedAssistants, assistant, callFiltering, screening) | CUCM Manager/Assistant (IP Manager Assistant service) | No | No | No | **YES** | High |
| 34 | **Executive Assistant Settings** | `GET/PUT /people/{id}/features/executiveAssistant` | CUCM Assistant Console | No | No | No | **YES** | High |

### Analysis — Permissions

**Fully covered (1):** Outgoing Permissions are properly mapped from CSS analysis to calling permission types.

**Partial (1):** Incoming Permissions relate to CSS filtering but no dedicated mapper produces `IncomingPermissions` objects for Webex.

**Gaps (6):** Access Codes, Transfer Numbers, Digit Patterns, Call Policies, and the full Executive/Assistant suite are not covered.

**Executive/Assistant is the highest-priority gap in the entire audit.** CUCM Manager/Assistant (IPMA) is widely deployed. The Webex Executive/Assistant API has 8+ admin endpoints covering alert settings, assistant assignment, call filtering criteria, and screening. None of this is discovered, mapped, or configured by the pipeline. This is a common CUCM feature — any site with executive admins likely uses it.

---

## Category 4: Behavior & Devices

Settings controlling calling behavior, application/device configuration, shared lines, hoteling, and related features.

| # | Setting Name | Webex API Path (Admin) | CUCM Equivalent | Discovered? | Mapped? | Configured? | Gap? | Priority |
|---|-------------|----------------------|-----------------|-------------|---------|-------------|------|----------|
| 35 | **Monitoring (BLF)** | `PUT /people/{id}/features/monitoring` | Phone busyLampField entries | Yes | Yes (monitoring_mapper) | Yes (handle_monitoring_list_configure) | No | -- |
| 36 | **Push-to-Talk** | `GET/PUT /people/{id}/features/pushToTalk` | No direct CUCM equivalent (Cisco Jabber PTT is client-side) | N/A | No | No | **YES** | Low |
| 37 | **Privacy** | `PUT /people/{id}/features/privacy` | Phone enablePrivacy | Yes | Yes (call_settings_mapper) | Yes (handle_user_configure_settings) | No | -- |
| 38 | **Barge-In** | `PUT /people/{id}/features/bargeIn` | Phone-level (implied from privacy/partition settings) | Partial | No | No | **YES** | Low |
| 39 | **Calling Behavior** | `PUT /people/{id}/features/callingBehavior` | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 40 | **Application Services (Shared Line Appearance)** | `PUT /people/{id}/features/applications` + `PUT /telephony/config/people/{id}/applications/members` | CUCM Shared Line Appearance (multiple devices on same DN) | Yes (shared_line analyzer) | Yes | Yes (handle_shared_line_configure) | No | -- |
| 41 | **Hoteling** | `PUT /people/{id}/features/hoteling` + `PUT /telephony/config/people/{id}/devices/settings/hoteling` | CUCM Extension Mobility (enableExtensionMobility) | Partial (workspace_mapper detects for common-area) | No person-level mapper | No person-level handler | **YES** | High |
| 42 | **Hot Desking (Voice Portal)** | `GET/PUT /telephony/config/people/{id}/features/hotDesking/guest` | CUCM Extension Mobility | Partial | No | No | **YES** | Medium |
| 43 | **Receptionist Client** | `GET/PUT /people/{id}/features/reception` | CUCM Attendant Console | No | No | No | **YES** | Medium |
| 44 | **Numbers (Assign/Unassign)** | `PUT /telephony/config/people/{id}/numbers` | CUCM DN assignment (handled during user creation) | Yes | Yes (line_mapper) | Yes (during user:create) | No | -- |
| 45 | **Preferred Answer Endpoint** | `GET/PUT /telephony/config/people/{id}/preferredAnswerEndpoint` | No direct CUCM equivalent | N/A | No | No | **YES** | Low |
| 46 | **MS Teams Integration** | `GET/PUT /telephony/config/people/{id}/settings/msTeams` | No CUCM equivalent | N/A | No | No | **YES** | Low |
| 47 | **Mode Management** | `GET/PUT /telephony/config/people/{id}/modeManagement/features` | CUCM Time-of-Day CSSes (different architecture) | No | No | No | **YES** | Low |
| 48 | **Personal Assistant** | `GET/PUT /telephony/config/people/{id}/features/personalAssistant` | No CUCM equivalent (new Webex AI feature) | N/A | No | No | **YES** | Low |
| 49 | **Emergency Callback Number (ECBN)** | `GET/PUT /telephony/config/people/{id}/emergencyCallbackNumber` | CUCM ELIN groups + device pool E911 settings | Yes (e911_mapper) | Partial (advisory only) | No | **YES** | High |
| 50 | **Device Settings (Person)** | `GET/PUT /telephony/config/people/{id}/devices/settings` | CUCM Phone product-specific config | Yes | Yes (device_mapper) | Yes (handle_device_configure_settings) | No | -- |

### Analysis — Behavior & Devices

**Fully covered (5):** Monitoring, Privacy, Shared Line Appearance, Number assignment, and Device Settings have full pipelines.

**Partial (1):** Barge-In is related to Privacy settings in CUCM but has its own Webex endpoint. The call_settings_mapper extracts `enablePrivacy` but not barge-in state separately.

**Gaps (10):** Push-to-Talk, Calling Behavior, Hoteling (person-level), Hot Desking, Receptionist Client, Preferred Answer Endpoint, MS Teams, Mode Management, Personal Assistant, and ECBN configuration.

**Hoteling (person-level) is a high-priority gap.** CUCM Extension Mobility is very common. The workspace_mapper detects `enableExtensionMobility` for common-area phones but there's no person-level hoteling mapper. The Webex hoteling API (`PUT /people/{id}/features/hoteling`) enables/disables hoteling for a person, and the device-level hoteling endpoint (`PUT .../devices/settings/hoteling`) controls it per-device.

**ECBN is high-priority.** The e911_mapper produces advisory decisions about E911 architecture but doesn't configure per-person ECBN. In Webex, each person needs an Emergency Callback Number assigned.

---

## Category 5: Workspace-Specific Settings

Settings available for workspaces via `/telephony/config/workspaces/{id}/*` and `/workspaces/{id}/features/*`.

| # | Setting Name | Webex API Path | CUCM Equivalent | Discovered? | Mapped? | Configured? | Gap? | Priority |
|---|-------------|---------------|-----------------|-------------|---------|-------------|------|----------|
| 51 | **Workspace Call Forwarding** | `PUT /workspaces/{id}/features/callForwarding` | Common-area phone line forwarding | No | No | No | **YES** | Medium |
| 52 | **Workspace Call Waiting** | `PUT /workspaces/{id}/features/callWaiting` | Common-area phone line call waiting | No | No | No | **YES** | Low |
| 53 | **Workspace Caller ID** | `PUT /workspaces/{id}/features/callerId` | Common-area phone CPN settings | No | No | No | **YES** | Low |
| 54 | **Workspace Call Recording** | `PUT /telephony/config/workspaces/{id}/features/callRecordings` | Common-area phone BIB status | No | No | No | **YES** | Low |
| 55 | **Workspace Call Intercept** | `PUT /workspaces/{id}/features/intercept` + greeting upload | N/A | N/A | No | No | **YES** | Low |
| 56 | **Workspace Incoming Permissions** | `PUT /workspaces/{id}/features/incomingPermission` | N/A | N/A | No | No | **YES** | Low |
| 57 | **Workspace Outgoing Permissions** | `PUT /workspaces/{id}/features/outgoingPermission` + access codes + transfer numbers | CSS-based restrictions on common-area phones | No | No | No | **YES** | Medium |
| 58 | **Workspace Monitoring** | `PUT /workspaces/{id}/features/monitoring` | BLF on common-area phones | No | No | No | **YES** | Low |
| 59 | **Workspace Voicemail** | `PUT /telephony/config/workspaces/{id}/voicemail` + greeting uploads | Common-area phone VM profile | No | No | No | **YES** | Medium |
| 60 | **Workspace Music on Hold** | `PUT /telephony/config/workspaces/{id}/musicOnHold` | Device Pool MOH source ref | No | No | No | **YES** | Low |
| 61 | **Workspace DND** | `PUT /telephony/config/workspaces/{id}/doNotDisturb` | Common-area phone DND status | No | No | No | **YES** | Low |
| 62 | **Workspace Barge-In** | `PUT /telephony/config/workspaces/{id}/bargeIn` | N/A | N/A | No | No | **YES** | Low |
| 63 | **Workspace Call Bridge** | `PUT /telephony/config/workspaces/{id}/callBridge` | N/A | N/A | No | No | **YES** | Low |
| 64 | **Workspace Privacy** | `PUT /telephony/config/workspaces/{id}/privacy` | Common-area phone enablePrivacy | No | No | No | **YES** | Low |

Note: Workspace settings marked "N/A" for CUCM Equivalent have no common-area phone equivalent in CUCM (these are Webex-native features). Settings requiring Professional Workspace license are noted — Basic Workspace gets 405 on most `/telephony/config/workspaces/` endpoints (only `musicOnHold` and `doNotDisturb` work on Basic).

Additionally, workspace-level Selective rules (Accept/Forward/Reject), Sequential Ring, Simultaneous Ring, and Priority Alert exist in the API but are omitted from this table as they are niche and have no CUCM equivalent for common-area phones.

### Analysis — Workspace-Specific

**Fully covered (0):** The `handle_workspace_configure_settings` handler exists and can write any `call_settings` dict to `/workspaces/{id}/features/{feature}`, but **no mapper currently populates `call_settings` on CanonicalWorkspace objects.** The workspace_mapper creates the workspace object (display name, location, extension, device type, license tier) but does not extract any per-workspace call settings from the CUCM common-area phone data.

**This is the single largest coverage gap by volume** — 14 settings with no pipeline coverage. However, most common-area phones in CUCM have default settings (no forwarding, no recording, no custom VM), so the practical impact is moderate.

**Workspace Call Forwarding and Workspace Voicemail are the highest-priority workspace gaps** for sites with conference room phones that have forwarding rules or VM configured.

---

## Top Priority Gaps (Ordered)

These are the settings most likely to be configured in a real CUCM environment and most impactful to miss during migration:

| Rank | Setting | Priority | Rationale |
|------|---------|----------|-----------|
| 1 | **Executive/Assistant (8+ endpoints)** | HIGH | CUCM Manager/Assistant (IPMA) is widely deployed. Webex has full admin API. Zero pipeline coverage. |
| 2 | **Hoteling (Person-level)** | HIGH | CUCM Extension Mobility is very common. Webex hoteling API exists. No person-level mapper. |
| 3 | **ECBN (Per-person)** | HIGH | Required for E911 compliance. e911_mapper produces advisory only, doesn't configure per-person ECBN. |
| 4 | **Call Intercept** | MEDIUM | Used for suspended/terminated users. Admin API exists. No mapper or handler. |
| 5 | **Incoming Permissions** | MEDIUM | CSS analysis touches this territory but doesn't produce Webex IncomingPermissions objects. |
| 6 | **Outgoing Access Codes (FAC)** | MEDIUM | CUCM FAC is common in enterprises. Webex per-user access codes API exists. |
| 7 | **Outgoing Digit Patterns (Per-user)** | MEDIUM | CSS mapper detects blocking patterns but doesn't produce per-user digit pattern objects. |
| 8 | **Agent Caller ID** | MEDIUM | Important for call center agents. Separate from regular Caller ID. |
| 9 | **Person-level MOH** | MEDIUM | Per-user MOH override (rare but exists). moh_mapper is location-level only. |
| 10 | **Receptionist Client** | MEDIUM | CUCM Attendant Console users need Webex Receptionist Client configured. |
| 11 | **VM PIN Reset / Passcode** | MEDIUM | Post-migration VM access. Currently no automated path. |
| 12 | **Workspace Call Forwarding** | MEDIUM | Common-area phones with forwarding rules. |
| 13 | **Workspace Voicemail** | MEDIUM | Common-area phones with VM profiles. |
| 14 | **Workspace Outgoing Permissions** | MEDIUM | Common-area phones with restricted dialing. |
| 15 | **Barge-In (separate from Privacy)** | LOW | Related to Privacy but separate Webex endpoint. |
| 16 | **All user-only settings** | LOW | Simultaneous Ring, Sequential Ring, Priority Alert — no admin API, must be user-configured. |
| 17 | **Webex-native features** | LOW | Call Captions, Personal Assistant, MS Teams, Mode Management — no CUCM equivalent. |

---

## What's Working Well

The pipeline has solid coverage for the **core user settings** that matter most in CUCM migrations:

1. **Call Forwarding (CFA/CFB/CFNA)** — Full pipeline: per-line forwarding extracted, mapped to Webex format, handler writes it. Lossy variants (BusyInt, NoAnswerInt, etc.) correctly flagged.
2. **DND** — Extracted from phone dndStatus, maps to Webex enablement + ringSplash.
3. **Call Waiting** — Extracted from per-line callWaiting.
4. **Caller ID** — Extracted from callerIdBlock, maps to Webex CLID policy.
5. **Privacy** — Extracted from enablePrivacy.
6. **Call Recording** — Extracted from builtInBridgeStatus.
7. **Voicemail** — Full pipeline with Unity Connection integration, 10-row gap analysis for UC features without Webex equivalent, custom greeting detection.
8. **Monitoring (BLF)** — Full pipeline: BLF entries extracted from phones, resolved to user targets, configured as monitoring list.
9. **Single Number Reach** — Full pipeline: Remote Destinations mapped to SNR numbers, lossy timer decisions.
10. **Outgoing Permissions** — CSS analysis produces calling permission types mapped to Webex outgoing permission call types.
11. **Shared Line Appearance** — SharedLineAnalyzer + handler for configuring SCA members.
12. **Device Settings** — Per-device settings configured via handler.
13. **Device Layout** — Line key templates + per-phone layout configured.
14. **Softkey Config** — PSK mappings for 9861/8875 devices.
15. **Number Assignment** — Handled during user/workspace creation.

---

## Recommendations

### Immediate (Before Next Migration)

1. **Add ECBN per-person configuration** — After user creation, set ECBN to the user's DID or location main number. This is required for E911 compliance and should be a Tier 5 operation.

2. **Add hoteling person-level mapper** — Detect CUCM `enableExtensionMobility` on user-associated phones and produce a `PUT /people/{id}/features/hoteling` call with `{enabled: true}`.

### Short-Term (Next Pipeline Iteration)

3. **Add Executive/Assistant mapper** — Requires new discovery (AXL `listCtiRoutePoint` or `executiveAssistant` service config). Produce executive/assistant pairings and call filtering criteria.

4. **Add Call Intercept mapper** — Detect CUCM line/device intercept status and map to Webex Call Intercept settings.

5. **Add workspace call settings enrichment** — Extract forwarding, DND, VM from common-area phone data in `workspace_mapper.py` and populate `call_settings` dict on `CanonicalWorkspace`.

### Medium-Term

6. **Add Incoming Permissions mapper** — Derive from CSS analysis whether a user has restricted incoming call types.

7. **Add Barge-In as separate setting** — Currently rolled into Privacy; Webex has a separate barge-in endpoint.

8. **Add Receptionist Client mapper** — Detect CUCM Attendant Console usage and flag for Webex Receptionist Client configuration.

### Not Needed for Migration

9. **User-only settings** (Simultaneous Ring, Sequential Ring, Priority Alert, Call Notify) — No admin API path. Document as "user self-configures post-migration."

10. **Webex-native features** (Call Captions, Personal Assistant, MS Teams, Mode Management) — No CUCM equivalent. These are net-new Webex features to enable post-migration if desired.
