# Person & Workspace Settings: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

## Decision Framework

### VOICEMAIL_INCOMPATIBLE
CUCM Unity Connection voicemail maps to Webex per-user voicemail. The CFNA timeout conversion formula is `rings = cfna_timeout // 6` (integer division). Default when no Unity data: 3 rings. Unity Connection features (MWI, VM-to-email, fax) have Webex voicemail equivalents but require explicit configuration. Voicemail pilot objects don't migrate as separate entities -- Webex voicemail is per-user with location-level configuration.
<!-- Source: recommendation_rules.py recommend_voicemail_incompatible(), advisory_patterns.py detect_voicemail_pilot_simplification() -->

### WORKSPACE_LICENSE_TIER
Professional vs Basic workspace license. Professional required if the workspace uses ANY of: `callForwarding`, `callerId`, `monitoring`, `intercept`, `callWaiting`, `callRecording`, `bargeIn`, `pushToTalk`. Basic workspaces only support `musicOnHold` and `doNotDisturb` at the `/telephony/config/workspaces/{id}/` path. For Basic workspaces, 7 endpoints work at the `/workspaces/{id}/features/` path: callForwarding, callWaiting, callerId, intercept, monitoring, incomingPermission, outgoingPermission.
<!-- Source: recommendation_rules.py _PROFESSIONAL_FEATURES, _BASIC_FEATURES; devices-workspaces.md gotcha #10 (verified via live API 2026-03-19, matrix completed 2026-03-27) -->

### WORKSPACE_TYPE_UNCERTAIN
Conference phone models (7832, 8832, CP-7832, CP-8832, 7832-CE, 8832-CE) map to `conference_room`. Desk phone models without an assigned owner map to `common_area`. Mixed signals (e.g., conference model with a user assignment) return no recommendation (ambiguous).
<!-- Source: recommendation_rules.py recommend_workspace_type_uncertain(), _CONFERENCE_MODELS, _DESK_PHONE_MODELS -->

### SHARED_LINE_COMPLEX
Appearance count <= 10 with mixed or non-monitoring labels: `shared_line` (Webex supports up to 35 appearances). ALL secondary labels contain monitoring keywords (BLF, Monitor, Busy Lamp, Speed, DSS): `virtual_extension`. Appearance count > 10 with mixed usage: returns None (ambiguous, requires human decision). The advisory pattern `shared_line_simplification` cross-checks decisions post-hoc and flags monitoring-only shared lines that should be virtual extensions.
<!-- Source: recommendation_rules.py recommend_shared_line_complex(), _MONITORING_KEYWORDS; advisory_patterns.py detect_shared_line_simplification() -->

### FORWARDING_LOSSY
Always returns `accept_loss`. CUCM has 10 forwarding variants: CFA, CFB, CFNA + 7 CUCM-only (busyInt, noAnswerInt, noCoverage, noCoverageInt, onFailure, notRegistered, notRegisteredInt). Webex supports 3: Always, Busy, No Answer + Business Continuity. The 7 CUCM-only variants are rarely intentionally configured -- CFA/CFB/CFNA covers >95% of real forwarding behavior.
<!-- Source: recommendation_rules.py recommend_forwarding_lossy() -->

### SNR_LOSSY
Always returns `accept_loss`. CUCM Single Number Reach has timer controls (answerTooSoon, answerTooLate thresholds) that don't exist in Webex. Webex SNR provides `answerConfirmationEnabled` (prompt to press key before connecting) as the equivalent "don't connect too soon" behavior but no numeric timer controls. Manual setup required per user.
<!-- Source: recommendation_rules.py recommend_snr_lossy(); advisory_patterns.py detect_snr_configured_users() -->

## Call Forwarding Chain Translation

CUCM forwarding → Webex mapping:

| CUCM Setting | Webex Equivalent | Field Path | Notes |
|--------------|-----------------|------------|-------|
| CFA (Call Forward All) | `callForwarding.always` | `enabled`, `destination`, `ringReminderEnabled` | Direct map |
| CFB (Call Forward Busy) | `callForwarding.busy` | `enabled`, `destination` | Direct map |
| CFNA (Call Forward No Answer) | `callForwarding.noAnswer` | `enabled`, `destination`, `numberOfRings` | `numberOfRings` = cfna_timeout // 6 |
| Business Continuity | `businessContinuity` | `enabled`, `destination` | CUCM equivalent: "unregistered" forwarding (phone offline) |
| busyInt, noAnswerInt | No equivalent | -- | Internal-only variants; CUCM-specific |
| noCoverage, noCoverageInt | No equivalent | -- | Coverage path variants; CUCM-specific |
| onFailure | No equivalent | -- | CUCM-specific |
| notRegistered, notRegisteredInt | Partial via Business Continuity | -- | Business Continuity covers the unregistered case but not internal-only |
<!-- Source: person-call-settings-handling.md sec 1 (CallForwardingPerson model); recommendation_rules.py recommend_forwarding_lossy() -->

## Voicemail Mapping

| Unity Connection Feature | Webex Voicemail Equivalent | Notes |
|--------------------------|---------------------------|-------|
| Voicemail enabled | `voicemail.enabled` | Direct map |
| Greeting (busy/no-answer) | `sendBusyCalls.greeting`, `sendUnansweredCalls.greeting` | DEFAULT or CUSTOM; custom requires upload |
| CFNA ring count | `sendUnansweredCalls.numberOfRings` | Formula: `cfna_timeout // 6` (e.g., 24s = 4 rings) |
| Message Waiting Indicator | `messageStorage.mwiEnabled` | Default: true |
| VM-to-email | `emailCopyOfMessage.enabled` | Webex sends audio attachment to configured email |
| Fax reception | `faxMessage.enabled` | Default: disabled |
| Transfer to 0 | `transferToNumber` | Destination number for "press 0" during greeting |
| VM forwarding | `voiceMessageForwardingEnabled` | Read-only in Webex |
| External message storage | `messageStorage.storageType` | INTERNAL (default) or EXTERNAL |
<!-- Source: person-call-settings-media.md sec 1 (VoicemailSettings model); recommendation_rules.py recommend_voicemail_incompatible() -->

## Edge Cases & Exceptions

- **Shared lines where some appearances are monitoring AND some are active call handling.** The rule checks if ALL secondary labels match monitoring keywords. Mixed usage returns None (ambiguous). The advisory pattern `shared_line_simplification` only fires when ALL secondary appearances in a decision are monitoring-only.
<!-- Source: recommendation_rules.py recommend_shared_line_complex() lines 294-300 -->

- **Workspaces that use callForwarding only for after-hours routing.** The `_PROFESSIONAL_FEATURES` set includes `callForwarding`, so any forwarding triggers a Professional recommendation. But forwarding works on Basic via the `/workspaces/{id}/features/callForwarding` path. The rule is conservative -- it recommends Professional because the `/telephony/config/` path (which has more settings) requires it.
<!-- Source: devices-workspaces.md gotcha #10 endpoint access matrix -->

- **Recording-enabled users where recording was enabled org-wide but never used.** The advisory pattern `recording_enabled_users` scans CUCM phone lines for `recordingFlag` != "Call Recording Disabled". It cannot distinguish org-wide policy from intentional per-user enablement. Webex requires a separate recording license + location-level vendor configuration + person-level recording settings.
<!-- Source: advisory_patterns.py detect_recording_enabled_users(); location-call-settings-advanced.md sec 1 -->

- **SNR users who customized answerTooSoon/answerTooLate timers.** These timer controls are CUCM-specific. Webex SNR has no timer fields -- only `answerConfirmationEnabled` (boolean). The `detect_snr_configured_users` pattern flags all remote destination profiles as needing manual setup but doesn't distinguish customized timers from defaults.
<!-- Source: recommendation_rules.py recommend_snr_lossy(); person-call-settings-handling.md sec 6 (SingleNumberReachNumber model) -->

- **Voicemail pilots across multiple Unity Connection systems.** The `voicemail_pilot_simplification` pattern only fires when ALL pilots share the same voicemail system (same pilot number prefix). Multi-system deployments are left alone for manual review.
<!-- Source: advisory_patterns.py detect_voicemail_pilot_simplification() -->

## Real-World Patterns

- **"executive assistant"**: Executive + assistant with shared lines and monitoring. Shared line for the executive DN, BLF monitoring for presence. In Webex: shared line appearance + executive/assistant feature pairing. Note: executive screening/filtering are admin-configurable but callPolicies is user-only (no admin API path).
<!-- Source: person-call-settings-handling.md admin vs user-only table; person-call-settings-permissions.md sec 5 -->

- **"lobby phone"**: Desk phone in common area, no forwarding, no voicemail. Maps to Basic workspace (`common_area` type). Only needs musicOnHold and DND -- both work on Basic license.
<!-- Source: recommendation_rules.py recommend_workspace_type_uncertain(), recommend_workspace_license_tier() -->

- **"hot desk"**: CUCM Extension Mobility maps to Webex hoteling. User logs into any hoteling-enabled device temporarily. Configured via `hoteling` workspace setting or person-level `hoteling` behavior setting.
<!-- Source: person-call-settings-behavior.md (hoteling section) -->

- **"recording compliance"**: All users recording-enabled in CUCM. In Webex: configure at location level first (vendor, compliance announcements, storage), then enable per-person recording settings. Requires separate call recording license.
<!-- Source: location-call-settings-advanced.md sec 1; advisory_patterns.py detect_recording_enabled_users() -->

- **"VM to email"**: Unity Connection VM-to-email maps to Webex `emailCopyOfMessage.enabled` with the user's email address. Webex sends the voicemail audio file as an email attachment.
<!-- Source: person-call-settings-media.md sec 1 (VoicemailSettings model) -->

## Webex Constraints

- **6 person settings are user-only (no admin API path):** `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, `callPolicies`. These exist only at `/telephony/config/people/me/settings/{feature}` and require user-level OAuth. An admin cannot read or write these for another user. `callPolicies` is additionally marked beta.
<!-- Source: self-service-call-settings.md sec 2 summary table; person-call-settings-handling.md admin vs user-only table; CLAUDE.md known issue #4 -->

- **Two path families for person settings.** Classic: `/people/{personId}/features/{feature}`. Newer: `/telephony/config/people/{personId}/{feature}`. Name differences: `intercept` (not `callIntercept`), `reception` (not `receptionist`), `applications` (not `applicationServicesSettings`), `autoTransferNumbers` (not `transferNumbers`), `pushToTalk` (not `pushToTalkSettings`).
<!-- Source: CLAUDE.md known issue #5 -->

- **Workspace `/telephony/config/` settings require Professional license.** Basic workspaces get 405 "Invalid Professional Place" on all `/telephony/config/workspaces/{id}/` endpoints except `musicOnHold` and `doNotDisturb`. The `/workspaces/{id}/features/` path works on Basic for: callForwarding, callWaiting, callerId, intercept, monitoring, incomingPermission, outgoingPermission.
<!-- Source: devices-workspaces.md gotcha #10 (verified via live API 2026-03-19, matrix completed 2026-03-27); CLAUDE.md known issue #6 -->

- **Recording requires separate license + location-level config.** Org-level recording must be enabled, a vendor must be selected (or Webex Recording Platform), and compliance announcement settings configured at the location level. Only then can person-level `callRecording` be enabled.
<!-- Source: location-call-settings-advanced.md sec 1; person-call-settings-media.md sec 7 -->

- **Max 35 shared line appearances.** Webex shared lines support up to 35 appearances per DN.
<!-- From training, needs verification -->

## Dissent Triggers

### DT-USER-001: Shared line recommended but appearance count approaches 35 limit
- **Condition:** SHARED_LINE_COMPLEX recommends `shared_line` AND total shared line appearances per device exceeds 25
- **Why static rule misses this:** Each SHARED_LINE_COMPLEX decision is evaluated independently per DN. No cross-decision aggregation of total appearances per device.
- **Advisor should:** Flag in cross-decision analysis. If a single device has shared lines from multiple DNs totaling >25 appearances, recommend converting some monitoring-only lines to virtual extensions.
- **Confidence:** LOW
<!-- Source: recommendation_rules.py recommend_shared_line_complex() only checks appearance_count per DN -->

### DT-USER-002: Workspace classified as Basic but has forwarding configured for business continuity
- **Condition:** WORKSPACE_LICENSE_TIER recommends `basic` BUT the CUCM workspace has CFNA/CFB configured (forwarding exists in CUCM data)
- **Why static rule misses this:** The rule checks `features_detected` against Webex feature names (`_PROFESSIONAL_FEATURES`). If the CUCM forwarding config wasn't mapped to Webex feature names before the decision runs, it won't trigger Professional. Additionally, callForwarding works on Basic via the `/workspaces/{id}/features/` path, so Basic may actually be correct -- but the user should know forwarding exists.
- **Advisor should:** Check if CUCM forwarding config exists in the source data and flag it as an informational finding. If forwarding is only CFNA-to-voicemail (standard behavior), Basic is fine. If forwarding to external numbers for business continuity, verify the `/features/` path supports the full forwarding model.
- **Confidence:** MEDIUM
<!-- Source: recommendation_rules.py recommend_workspace_license_tier(); devices-workspaces.md endpoint access matrix -->

### DT-USER-003: User-only settings cannot be migrated via admin API
- **Condition:** CUCM user has simultaneousRing, sequentialRing, or callPolicies configured AND migration uses admin-level OAuth
- **Why static rule misses this:** No decision type covers user-only setting migration. The 6 user-only settings require user-level OAuth tokens -- admin tokens get 404.
- **Advisor should:** Flag users with these CUCM features as requiring post-migration manual configuration or user-assisted setup. Bulk migration of these settings is not possible via admin API.
- **Confidence:** HIGH
<!-- Source: self-service-call-settings.md sec 2; person-call-settings-handling.md admin vs user-only table -->

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | 6 user-only settings list | Yes | `self-service-call-settings.md` lines 53-64; `person-call-settings-handling.md` lines 30-36 | simultaneousRing, sequentialRing, priorityAlert, callNotify, anonymousCallReject, callPolicies — exact match across both docs. |
| 2 | Workspace Basic limited to musicOnHold + DND | Yes | `devices-workspaces.md` gotcha #10 (verified 2026-03-27); CLAUDE.md known issue #6 | Under `/telephony/config/workspaces/{id}/`, only musicOnHold and doNotDisturb work on Basic. Full endpoint matrix confirms. |
| 3 | rings = cfna_timeout // 6 | Yes | `recommendation_rules.py` lines 434-441 | `rings = cfna_timeout // 6` (integer division) confirmed in source code. |
