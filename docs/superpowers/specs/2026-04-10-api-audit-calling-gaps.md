# API Audit: Webex Cloud Calling Spec vs CUCM Migration Pipeline

**Date:** 2026-04-10
**Source:** `specs/webex-cloud-calling.json` (161K lines, OpenAPI 3.0)
**Pipeline:** `src/wxcli/migration/` (20 mappers, 31 handlers, 25 expanders)

## Methodology

Extracted all PUT/POST endpoints from the Webex Cloud Calling spec that represent configurable settings. Cross-referenced against:
- **Mappers** (`transform/mappers/`): 20 mapper classes that read CUCM data and produce canonical objects
- **Handlers** (`execute/handlers.py`): 31 handler functions in `HANDLER_REGISTRY` that call Webex APIs
- **Expanders** (`execute/planner.py`): 25 entries in `_EXPANDERS` that generate execution operations

Filtered to CUCM-migration-relevant endpoints only (excluded Webex-only features with no CUCM equivalent).

---

## Current Pipeline Coverage Summary

### What the pipeline DOES handle (31 handlers):

| Tier | Resource Types |
|------|---------------|
| 0 | location:create, location:enable_calling |
| 1 | trunk:create, route_group:create, operating_mode:create, schedule:create, line_key_template:create |
| 2 | user:create, workspace:create, dial_plan:create, translation_pattern:create |
| 3 | workspace:assign_number, device:create |
| 4 | hunt_group:create, call_queue:create, auto_attendant:create, call_park:create, pickup_group:create, paging_group:create |
| 5 | user:configure_settings (DND/callWaiting/callerId/privacy/callRecording), user:configure_voicemail, device:configure_settings, workspace:configure_settings, calling_permission:assign, call_forwarding:configure, single_number_reach:configure |
| 6 | shared_line:configure, virtual_line:create/configure, monitoring_list:configure |
| 7 | device_layout:configure, softkey_config:configure |

### Canonical types with mappers but NO execution handler:

| Type | Mapper | Purpose |
|------|--------|---------|
| `music_on_hold` | MOHMapper | Advisory only (AUDIO_ASSET_MANUAL decision) |
| `announcement` | AnnouncementMapper | Advisory only (AUDIO_ASSET_MANUAL decision) |
| `e911_config` | E911Mapper | Advisory only (ARCHITECTURE_ADVISORY decision) |
| `device_profile` | DeviceProfileMapper | Report data only (no Webex equivalent) |
| `location_schedule` | FeatureMapper | Consumed by AA/schedule creation (not standalone) |

---

## Person Settings Gaps

API endpoints at `/people/{personId}/features/*` and `/telephony/config/people/{personId}/*`.

| API Endpoint Group | What It Configures | Has Mapper? | Has Handler? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `features/applications` | Application Services (shared line appearance) | Yes (shared_line) | Yes (shared_line:configure) | COVERED | Via `/telephony/config/people/{id}/applications/members` |
| `features/bargeIn` | Barge-In settings | Partial | Partial | LOW | CallSettingsMapper extracts but only if recording is on; no barge-in-specific CUCM field. Passed via user:configure_settings generic dict |
| `features/callForwarding` | Call Forwarding (always/busy/no-answer) | Yes | Yes | COVERED | Dedicated CallForwardingMapper + handler |
| `features/callRecording` | Call Recording | Partial | Partial | LOW | CallSettingsMapper extracts builtInBridgeStatus. Passed via user:configure_settings |
| `features/callWaiting` | Call Waiting | Yes | Yes (generic) | COVERED | CallSettingsMapper extracts; passed via user:configure_settings |
| `features/callerId` | Caller ID (external name policy, block) | Yes | Yes (generic) | COVERED | CallSettingsMapper extracts; passed via user:configure_settings |
| `features/callingBehavior` | Calling behavior (native/app/mixed) | No | No | LOW | Webex-native concept. CUCM users default to native calling. No CUCM source data |
| `features/doNotDisturb` | Do Not Disturb | Yes | Yes (generic) | COVERED | CallSettingsMapper extracts dndStatus |
| `features/executiveAssistant` | Executive/Assistant pairing | No | No | **MEDIUM** | CUCM has Manager/Assistant relationship. Data exists in AXL but no mapper extracts it |
| `features/hoteling` | Hoteling (guest/host) | No | No | LOW | CUCM Extension Mobility is architecturally different. Advisory-only in practice |
| `features/incomingPermission` | Incoming call permissions | No | No | LOW | CUCM handles via CSS; Webex incoming permissions are simpler. Low migration value |
| `features/intercept` | Call Intercept (block incoming/outgoing) | No | No | **MEDIUM** | CUCM has per-line intercept. Could map to Webex call intercept during migration cutover |
| `features/monitoring` | Monitoring (BLF) | Yes | Yes | COVERED | MonitoringMapper + handler |
| `features/outgoingPermission` | Outgoing call permissions | Yes | Yes | COVERED | CSSMapper + calling_permission:assign handler |
| `features/privacy` | Privacy/line status | Partial | Partial | LOW | CallSettingsMapper extracts enablePrivacy. Passed via user:configure_settings |
| `features/pushToTalk` | Push-to-Talk | No | No | LOW | Rare in CUCM environments. No standard AXL extraction point |
| `features/reception` | Receptionist client settings | No | No | LOW | CUCM Attendant Console is a separate app, not a per-user setting |
| `features/schedules` | Per-user schedules | No | No | LOW | CUCM schedules are per-feature (AA), not per-user |
| `features/voicemail` | Voicemail settings | Yes | Yes | COVERED | VoicemailMapper + user:configure_voicemail handler |
| `{personId}/callCaptions` | Call captions / real-time transcription | No | No | SKIP | Webex-only feature, no CUCM equivalent |
| `{personId}/emergencyCallbackNumber` | ECBN | No | No | **MEDIUM** | CUCM ECBN data exists but E911Mapper only does advisory. No execution handler |
| `{personId}/executive/*` | Executive alert/screening/filtering/assistants | No | No | **MEDIUM** | Same as executiveAssistant above. 6 sub-endpoints for the full exec/assistant workflow |
| `{personId}/musicOnHold` | Per-person MOH | No | No | LOW | CUCM MOH is per-location/class. MOHMapper produces advisory. Per-person MOH is rare |
| `{personId}/numbers` | Number assignment | Partial | Partial | LOW | Handled during user:create (extension/phoneNumber). Separate number management not needed for migration |
| `{personId}/outgoingPermission/accessCodes` | Access codes for outgoing | No | No | LOW | CUCM FAC/CMC. CSSMapper handles permissions but not access codes specifically |
| `{personId}/outgoingPermission/digitPatterns` | Digit patterns for person permissions | No | No | LOW | Org-level dial plans handle the equivalent function |
| `{personId}/outgoingPermission/autoTransferNumbers` | Auto transfer numbers | No | No | LOW | No direct CUCM equivalent |
| `{personId}/preferredAnswerEndpoint` | Preferred answer endpoint | No | No | LOW | Webex-native concept for multi-device users |
| `{personId}/selectiveAccept` | Selective call accept | No | No | LOW | CUCM has no equivalent selective accept feature |
| `{personId}/selectiveForward` | Selective call forwarding (rules-based) | No | No | **MEDIUM** | CUCM has conditional forwarding rules. CallForwardingMapper handles basic CFA/CFB/CFNA but not rule-based |
| `{personId}/selectiveReject` | Selective call rejection | No | No | LOW | CUCM has no equivalent selective reject feature |
| `{personId}/sequentialRing` | Sequential ring | No | No | LOW | No direct CUCM equivalent (SNR handles remote destinations separately) |
| `{personId}/simultaneousRing` | Simultaneous ring | No | No | LOW | No direct CUCM equivalent. SNRMapper handles remote destinations |
| `{personId}/singleNumberReach` | Single Number Reach | Yes | Yes | COVERED | SNRMapper + single_number_reach:configure handler |
| `{personId}/voicemail/passcode` | Voicemail passcode | No | No | LOW | Passcodes cannot be extracted from CUCM Unity. Users must reset |
| `{personId}/agent/callerId` | Agent caller ID (queue context) | No | No | LOW | Queue-specific agent settings, not general migration |
| `{personId}/settings/msTeams` | MS Teams integration setting | No | No | SKIP | Webex-only integration, no CUCM equivalent |
| `{personId}/features/callBridge` | Call bridge warning tone | No | No | LOW | Webex-native recording compliance feature |
| `{personId}/features/personalAssistant` | Personal assistant (Webex Assistant) | No | No | SKIP | Webex AI feature, no CUCM equivalent |
| `{personId}/features/hotDesking/guest` | Hot desking via voice portal | No | No | LOW | Webex-specific provisioning mechanism |
| `{personId}/devices/settings` | Device settings for a person | Yes | Yes | COVERED | device:configure_settings handler |
| `{personId}/devices/settings/hoteling` | Hoteling settings for person's devices | No | No | LOW | CUCM Extension Mobility is architectural. Advisory only |
| `{personId}/modeManagement/features` | Mode management feature assignment | No | No | SKIP | Webex-only operating mode management |

---

## Location Settings Gaps

API endpoints at `/telephony/config/locations/{locationId}/*`.

| API Endpoint Group | What It Configures | Has Mapper? | Has Handler? | Gap Priority | Notes |
|---|---|---|---|---|---|
| Enable calling | POST `/telephony/config/locations` | Yes | Yes | COVERED | location:enable_calling handler |
| Update details | PUT `/telephony/config/locations/{id}` | No | No | LOW | Initial values set at create time |
| Announcement language | `actions/modifyAnnouncementLanguage` | No | No | LOW | Set during location creation |
| Location announcements | `announcements` (POST/PUT) | No | No | **MEDIUM** | AnnouncementMapper produces advisory but no upload handler. Audio files need manual transfer |
| Auto Attendant | `autoAttendants` | Yes | Yes | COVERED | FeatureMapper + auto_attendant:create handler |
| AA call forwarding | `autoAttendants/{id}/callForwarding` | No | No | **MEDIUM** | AA forwarding rules not mapped from CUCM. Pipeline creates AA but not its forwarding rules |
| AA selective forwarding | `autoAttendants/{id}/callForwarding/selectiveRules` | No | No | LOW | No CUCM equivalent for AA-level selective forwarding |
| Call captions | `callCaptions` | No | No | SKIP | Webex-only feature |
| Call Park | `callParks` | Yes | Yes | COVERED | FeatureMapper + call_park:create handler |
| Call Park Extensions | `callParkExtensions` | No | No | LOW | Webex call park extensions are separate from call park groups. Pipeline creates parks with extensions inline |
| Call Park settings | `callParks/settings` (location-wide recall) | No | No | LOW | Default recall settings acceptable for migration |
| Call Pickup | `callPickups` | Yes | Yes | COVERED | FeatureMapper + pickup_group:create handler |
| Call Recording (location) | `callRecording/complianceAnnouncement`, `callRecording/vendor` | No | No | LOW | Org-level recording config. Not per-location in CUCM |
| Call Routing (location) | `callRouting/translationPatterns` (location-level) | No | No | LOW | Pipeline uses org-level translation patterns. Location-level is rare |
| DECT Networks | `dectNetworks/*` | No | No | **MEDIUM** | CUCM has no DECT data (DECT is provisioned differently). But if site has DECT, it needs separate provisioning |
| Emergency Call Notification | `emergencyCallNotification` | No | No | **MEDIUM** | CUCM E911 notification config exists. E911Mapper advisory-only |
| Emergency Callback Number | `features/emergencyCallbackNumber` | No | No | **MEDIUM** | Same as person-level ECBN. E911Mapper advisory-only |
| Hot Desking (voice portal) | `features/hotDesking` | No | No | LOW | Webex-specific provisioning mechanism |
| Hunt Groups | `huntGroups` | Yes | Yes | COVERED | FeatureMapper + hunt_group:create handler |
| HG call forwarding | `huntGroups/{id}/callForwarding` | No | No | **MEDIUM** | HG forwarding rules not mapped. Pipeline creates HG but not its forwarding rules |
| HG selective forwarding | `huntGroups/{id}/callForwarding/selectiveRules` | No | No | LOW | No CUCM equivalent |
| Location intercept | `intercept` | No | No | LOW | Emergency intercept at location level. Not a standard CUCM migration item |
| Internal dialing | `internalDialing` | No | No | LOW | Set during location enable. Default is acceptable |
| Music On Hold | `musicOnHold` | Advisory | No | **MEDIUM** | MOHMapper produces advisory (AUDIO_ASSET_MANUAL) but no execution handler to configure per-location MOH settings |
| Location numbers | `numbers` (POST/PUT) | No | No | LOW | Numbers assigned via user/workspace creation. Bulk number management is a pre-migration step |
| Outgoing permissions (location) | `outgoingPermission` | No | No | LOW | CSSMapper handles per-user permissions. Location-level defaults are acceptable |
| Outgoing permission access codes | `outgoingPermission/accessCodes` | No | No | LOW | CUCM FAC/CMC. Not a standard migration item |
| Outgoing permission digit patterns | `outgoingPermission/digitPatterns` | No | No | LOW | Org-level dial plans handle the equivalent |
| Outgoing auto transfer numbers | `outgoingPermission/autoTransferNumbers` | No | No | LOW | No CUCM equivalent |
| Paging Groups | `paging` | Yes | Yes | COVERED | FeatureMapper + paging_group:create handler |
| Private Network Connect | `privateNetworkConnect` | No | No | SKIP | Webex-only network topology feature |
| Call Queues | `queues` | Yes | Yes | COVERED | FeatureMapper + call_queue:create handler |
| CQ call forwarding | `queues/{id}/callForwarding` | No | No | **MEDIUM** | CQ forwarding rules not mapped. Pipeline creates CQ but not its forwarding rules |
| CQ selective forwarding | `queues/{id}/callForwarding/selectiveRules` | No | No | LOW | No CUCM equivalent |
| CQ forced forward | `queues/{id}/forcedForward` | No | No | LOW | Webex CQ-specific overflow feature |
| CQ holiday service | `queues/{id}/holidayService` | No | No | **MEDIUM** | CUCM TimeOfDay routing creates holiday schedules. Pipeline creates operating modes but doesn't wire CQ holiday service |
| CQ night service | `queues/{id}/nightService` | No | No | **MEDIUM** | Same as holiday: CUCM TimeOfDay routing → Webex night service not wired |
| CQ stranded calls | `queues/{id}/strandedCalls` | No | No | LOW | Webex CQ-specific overflow feature |
| CX Essentials screen pop | `queues/{id}/cxEssentials/screenPop` | No | No | SKIP | CX Essentials feature, no CUCM equivalent |
| CX Essentials wrap-up | `cxEssentials/locations/{id}/queues/{id}/wrapup/settings` | No | No | SKIP | CX Essentials feature |
| Receptionist directories | `receptionistContacts/directories` | No | No | LOW | CUCM Attendant Console is a separate app |
| RedSky E911 | `redSky/*` | No | No | **MEDIUM** | E911Mapper advisory-only. No execution handler for RedSky building/status |
| Schedules | `schedules` | Yes | Yes | COVERED | FeatureMapper + schedule:create handler |
| Voice Portal | `voicePortal` | No | No | LOW | CUCM voice portal is Unity-based. Webex voice portal has different architecture |
| Voicemail (location) | `voicemail` | No | No | LOW | Location-level VM settings (passcode rules, storage). Not typically customized per-site in CUCM |
| Voicemail Groups | `voicemailGroups` | No | No | **MEDIUM** | CUCM Unity hunt pilots → Webex voicemail groups. No mapper or handler |
| Operating Modes | `operatingModes` | Yes | Yes | COVERED | RoutingMapper/FeatureMapper + operating_mode:create handler |

---

## Workspace Settings Gaps

Two API path families: `/workspaces/{id}/features/*` (basic) and `/telephony/config/workspaces/{id}/*` (professional license required).

| API Endpoint Group | What It Configures | Has Mapper? | Has Handler? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `features/callForwarding` | Call Forwarding | No | No | **MEDIUM** | CallForwardingMapper only handles person-level. Common-area phones may have forwarding rules in CUCM |
| `features/callWaiting` | Call Waiting | No | No | LOW | Workspace call waiting rarely customized |
| `features/callerId` | Caller ID | No | No | LOW | Workspace caller ID rarely customized |
| `features/incomingPermission` | Incoming permissions | No | No | LOW | Default acceptable |
| `features/intercept` | Call Intercept | No | No | LOW | Not a standard CUCM workspace migration |
| `features/monitoring` | Monitoring (BLF) | No | No | LOW | Workspaces rarely have monitoring lists |
| `features/outgoingPermission` | Outgoing permissions | No | No | LOW | Default acceptable for workspaces |
| `features/outgoingPermission/accessCodes` | Access codes | No | No | LOW | Not applicable for workspaces |
| `config/workspaces/{id}/anonymousCallReject` | Anonymous call reject | No | No | LOW | Webex-specific |
| `config/workspaces/{id}/bargeIn` | Barge-In | No | No | LOW | Webex-specific |
| `config/workspaces/{id}/callBridge` | Call Bridge warning tone | No | No | LOW | Webex-specific |
| `config/workspaces/{id}/callPolicies` | Call policies | No | No | LOW | Webex-specific |
| `config/workspaces/{id}/devices` | Workspace devices | Yes | Yes | COVERED | Via workspace:create + device:create |
| `config/workspaces/{id}/devices/settings` | Device settings | No | No | LOW | Handled via device:configure_settings at device level |
| `config/workspaces/{id}/doNotDisturb` | DND | No | No | LOW | Rarely configured on common-area phones |
| `config/workspaces/{id}/emergencyCallbackNumber` | ECBN | No | No | LOW | E911 advisory covers this |
| `config/workspaces/{id}/features/callRecordings` | Recording | No | No | LOW | Rarely needed for workspaces |
| `config/workspaces/{id}/musicOnHold` | MOH | No | No | LOW | Location-level MOH applies |
| `config/workspaces/{id}/numbers` | Number assignment | Yes | Yes | COVERED | workspace:assign_number handler |
| `config/workspaces/{id}/outgoingPermission/digitPatterns` | Digit patterns | No | No | LOW | Org-level dial plans cover this |
| `config/workspaces/{id}/priorityAlert` | Priority alert | No | No | SKIP | Webex-only feature |
| `config/workspaces/{id}/privacy` | Privacy | No | No | LOW | Rarely configured on workspaces |
| `config/workspaces/{id}/pushToTalk` | Push-to-Talk | No | No | LOW | Rare for workspaces |
| `config/workspaces/{id}/selectiveAccept` | Selective accept | No | No | SKIP | No CUCM equivalent |
| `config/workspaces/{id}/selectiveForward` | Selective forward | No | No | LOW | No CUCM equivalent for workspaces |
| `config/workspaces/{id}/selectiveReject` | Selective reject | No | No | SKIP | No CUCM equivalent |
| `config/workspaces/{id}/sequentialRing` | Sequential ring | No | No | SKIP | No CUCM equivalent for workspaces |
| `config/workspaces/{id}/simultaneousRing` | Simultaneous ring | No | No | SKIP | No CUCM equivalent for workspaces |
| `config/workspaces/{id}/voicemail` | Voicemail | No | No | LOW | workspace:configure_settings handles if settings are present |
| `config/workspaces/{id}/voicemail/passcode` | Passcode | No | No | LOW | Cannot extract from CUCM |

---

## Org / Service Settings Gaps

API endpoints at `/telephony/config/*` (org-wide).

| API Endpoint Group | What It Configures | Has Mapper? | Has Handler? | Gap Priority | Notes |
|---|---|---|---|---|---|
| `config/announcements` (org-level) | Announcement repository | Advisory | No | **MEDIUM** | AnnouncementMapper produces advisory. No upload handler |
| `config/announcements/playlists` | Announcement playlists | No | No | LOW | Webex-only feature |
| `config/callRecording` | Org call recording settings | No | No | LOW | Org-level recording config is a pre-migration admin task |
| `config/callRecording/vendor` | Recording vendor | No | No | LOW | Pre-migration admin setup |
| `config/callerReputationProvider` | Caller reputation/SPAM | No | No | SKIP | Webex-only feature |
| `config/devices/lineKeyTemplates` | Line key templates | Yes | Yes | COVERED | ButtonTemplateMapper + line_key_template:create handler |
| `config/jobs/numbers/manageNumbers` | Bulk number management | No | No | LOW | Pre-migration number porting task |
| `config/premisePstn/dialPlans` | Dial plans | Yes | Yes | COVERED | CSSMapper + dial_plan:create handler |
| `config/premisePstn/routeGroups` | Route groups | Yes | Yes | COVERED | RoutingMapper + route_group:create handler |
| `config/premisePstn/routeLists` | Route lists | No | No | **HIGH** | CUCM route lists exist in AXL. RoutingMapper produces trunks + route groups but NOT route lists. Pipeline assumes route groups connect directly to trunks |
| `config/premisePstn/trunks` | Trunks | Yes | Yes | COVERED | RoutingMapper + trunk:create handler |
| `config/callRouting/translationPatterns` | Translation patterns | Yes | Yes | COVERED | RoutingMapper + translation_pattern:create handler |
| `config/operatingModes` | Operating modes | Yes | Yes | COVERED | RoutingMapper/FeatureMapper + operating_mode:create handler |
| `config/queues/agents/{id}/settings` | CX Essentials agent settings | No | No | SKIP | CX Essentials feature |
| `config/supervisors` | CX Essentials supervisors | No | No | SKIP | CX Essentials feature |
| `config/virtualExtensions` | Virtual extensions | No | No | LOW | Pipeline uses virtualLines, not virtualExtensions |
| `config/virtualExtensionRanges` | Virtual extension ranges | No | No | LOW | Bulk provisioning tool, not migration |
| `config/virtualLines` | Virtual lines | Yes | Yes | COVERED | virtual_line:create/configure handlers |
| `config/voicemail/rules` | Org voicemail rules | No | No | LOW | Pre-migration admin task |
| `config/voicemail/settings` | Org voicemail settings | No | No | LOW | Pre-migration admin task |

---

## Routing Infrastructure Gaps

| API Endpoint Group | What It Configures | Has Mapper? | Has Handler? | Gap Priority | Notes |
|---|---|---|---|---|---|
| Trunks | Create/modify | Yes | Yes | COVERED | |
| Route Groups | Create/modify | Yes | Yes | COVERED | |
| **Route Lists** | **Create/modify** | **No** | **No** | **HIGH** | **CUCM route lists are extracted but not mapped or created. The pipeline connects route groups directly to trunks, skipping the route list layer. This is architecturally correct for simple topologies but wrong for complex multi-site PSTN routing with failover** |
| Route List Numbers | Assign numbers to route list | No | No | **HIGH** | Depends on route list creation |
| Dial Plans | Create/modify | Yes | Yes | COVERED | |
| Dial Plan Patterns | Modify patterns on existing plan | No | No | LOW | Patterns set at creation time |
| Translation Patterns (org) | Create/modify | Yes | Yes | COVERED | |
| Translation Patterns (location) | Create/modify per-location | No | No | LOW | Pipeline uses org-level. Location-level is rare |

---

## Gap Priority Summary

### HIGH Priority (missing functionality that affects real migrations)

| Gap | API Endpoint | CUCM Source Data | Impact |
|-----|-------------|-----------------|--------|
| **Route Lists** | POST/PUT `/telephony/config/premisePstn/routeLists` | AXL routeList with routeGroup members | Multi-site PSTN failover requires route lists wrapping route groups. Without this, complex PSTN topologies flatten incorrectly |

### MEDIUM Priority (useful for completeness, workaround exists)

| Gap | API Endpoint | CUCM Source Data | Impact |
|-----|-------------|-----------------|--------|
| **Executive/Assistant** | PUT `/people/{id}/features/executiveAssistant`, `/executive/*` | AXL managerUserId/associatedUser | Manager/assistant call routing pairing lost. Manual reconfiguration needed |
| **Call Intercept** | PUT `/people/{id}/features/intercept` | AXL line-level intercept config | Intercept settings lost. Useful for staged migration cutover |
| **AA/HG/CQ Call Forwarding** | PUT `.../callForwarding` on AA/HG/CQ | CUCM forwarding on hunt pilots | Feature-level forwarding rules lost. Manual reconfiguration needed |
| **CQ Holiday/Night Service** | PUT `.../holidayService`, `.../nightService` | CUCM TimeOfDay routing | Schedule-based routing on queues lost. Operating modes created but not wired to CQ services |
| **ECBN (person + location)** | PUT `.../emergencyCallbackNumber` | AXL ECBN settings | Emergency callback numbers not configured. E911Mapper advisory only |
| **MOH Upload/Configure** | PUT `.../musicOnHold` | CUCM MOH audio sources | MOH advisory produced but no execution path. Audio must be manually uploaded |
| **Announcement Upload** | POST `.../announcements` | CUCM announcement files | Announcement advisory produced but no execution path |
| **Voicemail Groups** | POST `.../voicemailGroups` | CUCM Unity hunt pilots | Unity hunt pilot VM groups not mapped to Webex voicemail groups |
| **Location-level Announcements** | POST `.../locations/{id}/announcements` | CUCM announcements by partition | Location-scoped announcements not uploaded |
| **RedSky E911** | POST/PUT `.../redSky/*` | CUCM ELIN groups, geo locations | E911 advisory produced but no RedSky building/status configuration |
| **DECT Networks** | POST `.../dectNetworks` | CUCM has no direct DECT data | If site has DECT, requires separate provisioning. No mapper can extract from CUCM |
| **Selective Call Forwarding (person)** | PUT `.../selectiveForward` | CUCM conditional forwarding rules | Rule-based forwarding beyond CFA/CFB/CFNA not mapped |
| **Workspace Call Forwarding** | PUT `/workspaces/{id}/features/callForwarding` | CUCM common-area phone forwarding | Forwarding rules on common-area phones lost |

### LOW Priority (no CUCM equivalent, rare config, or acceptable defaults)

Covers 40+ endpoint groups including: callingBehavior, hoteling, pushToTalk, reception, per-user schedules, incoming permissions, access codes, digit patterns, auto transfer numbers, simultaneous/sequential ring, voicemail passcode, location-level outgoing permissions, call park settings, call park extensions, workspace DND/privacy/recording, org voicemail rules, virtual extensions, and all self-service `/people/me/` endpoints.

### SKIP (Webex-only, no CUCM equivalent)

Call captions, MS Teams integration, personal assistant, private network connect, caller reputation, CX Essentials (screen pop, wrap-up, agents, supervisors), priority alert, selective accept/reject (workspace), mode management (self-service), and WebexGo override.
