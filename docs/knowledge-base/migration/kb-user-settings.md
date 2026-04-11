# Person & Workspace Settings: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

> **Audience:** Migration advisor agent (Opus) and cold-context Claude sessions looking up dissent triggers, decision context, and Webex constraints for call forwarding, voicemail, calling permissions, and workspace licensing decisions.
> **Reading mode:** Reference. Grep by `DT-USER-NNN` ID for dissent triggers, OR read `## Decision Framework` end-to-end when the migration-advisor agent loads this doc during analysis.
> **See also:** [Operator Runbook](../../runbooks/cucm-migration/operator-runbook.md) · [Decision Guide](../../runbooks/cucm-migration/decision-guide.md) · [Tuning Reference](../../runbooks/cucm-migration/tuning-reference.md)

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

- **"call intercept"**: CUCM has no native call-intercept feature (a BroadSoft-heritage Webex setting for gracefully taking a line out of service — terminated employees, office relocations, leaves of absence, number changes). The migration pipeline heuristically detects *intercept-like* CUCM configurations via two SQL queries in `cucm/extractors/tier4.py`: (1) directory numbers in partitions whose **name** matches `%intercept%`, `%block%`, `%out_of_service%`, or `%oos%` (`signal_type="blocked_partition"`); (2) directory numbers with `callforwarddynamic.cfadestination` set and `cfavoicemailenabled='t'` where `NOT EXISTS` a registered phone backing the line (`signal_type="cfa_voicemail"`). Detected DNs become `intercept_candidate` objects keyed `intercept_candidate:{dn}:{partition}` and are cross-referenced to their owning user via `user_has_intercept_signal`. `CallSettingsMapper` (Pass 2) enriches each matched user's `call_settings.intercept = {detected, signal_type, forward_destination, voicemail_enabled}`. **Nothing is auto-configured** — detection surfaces as advisory Pattern 30 (`call_intercept_candidates`, severity `MEDIUM`, category `out_of_scope`) and in the assessment report (Appendix Y plus a conditional Executive Page 2 stat card). The operator configures Webex intercept manually post-cutover via `/people/{id}/features/intercept`, `/workspaces/{id}/features/intercept`, `/telephony/config/virtualLines/{id}/intercept`, or the location-level `/telephony/config/locations/{id}/intercept`. The person and workspace `/features/intercept` paths are available on all license tiers; the `/telephony/config/` variants require Professional. Heuristic false positives are expected — partition naming is a soft signal, and many CUCM admins use "block" in unrelated partition names (e.g., `BlockInternational_PT`), while `cfa_voicemail` can be an ordinary "send to voicemail" preference rather than an out-of-service configuration.
<!-- Source: cucm/extractors/tier4.py:_extract_intercept_candidates (lines 131-173); transform/normalizers.py:normalize_intercept_candidate; transform/cross_reference.py:_build_intercept_refs; transform/mappers/call_settings_mapper.py (Pass 2 intercept block); advisory/advisory_patterns.py:detect_call_intercept_candidates (Pattern 30); report/appendix.py:_intercept_candidates (Section Y); report/executive.py (intercept_count stat card); spec: docs/superpowers/specs/2026-04-10-call-intercept-migration.md -->

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

### DT-USER-004: Workspace recording-enabled lines silently miss Professional tier upgrade

**Condition:** WORKSPACE_LICENSE_TIER decision recommends `basic` AND the CUCM source
device has one or more lines with `recordingFlag` set to `Automatic` or `AppInvoked`
(i.e., call recording was active on this workspace phone).

**Why static rule fails:** `WorkspaceLicenseAnalyzer._detect_features()` in
`transform/analyzers/workspace_license.py` builds `features_detected` from two
sources: (1) `_PROFESSIONAL_INDICATORS` (hotdesking, DID) and (2) `_XREF_INDICATORS`
(voicemail, call forwarding, shared lines). Neither source checks CUCM `recordingFlag`
at the line level. As a result, recording-enabled workspace lines never populate
`features_detected` with `"callRecording"`. When `recommend_workspace_license_tier()`
in `advisory/recommendation_rules.py:103` checks `features_detected` against
`_PROFESSIONAL_FEATURES` (which includes `"callRecording"` at line 17), it never
finds a match and returns `"basic"`. The 405 response from
`/telephony/config/workspaces/{id}/callRecording` on a Basic workspace will fail
silently at execution time.
<!-- Source: workspace_license.py lines 43-53 + recommendation_rules.py lines 16-19 + 103-118; devices-workspaces.md gotcha #10 -->

**Advisor should:** When the recording advisory pattern (`recording_enabled_users` in
`advisory_patterns.py`) fires AND the affected objects include workspaces with a
`WORKSPACE_LICENSE_TIER: basic` decision, recommend overriding the tier to
`professional`. Do not defer to "accept the Basic recommendation" — the recording
endpoint will 405 at execution time, and the migrator will not see the failure until
post-execution validation.

**Confidence:** HIGH

**Signals to look for:** `recording_enabled_users` advisory finding present in the
store AND any of its `affected_objects` canonical IDs match a workspace with a
`WORKSPACE_LICENSE_TIER` decision recommending `basic`.

### DT-USER-005: Workspace type inference fails for conference models in private offices and unowned desk phones

**Condition:** WORKSPACE_TYPE_UNCERTAIN decision is present AND CUCM model is one of
`{7832, 8832, CP-7832, CP-8832}` (conference models) OR is in `_DESK_PHONE_MODELS`
with `has_owner = False`.

**Why static rule fails:** `recommend_workspace_type_uncertain()` in
`advisory/recommendation_rules.py:523` uses two hard-coded lookups:
(1) if `cucm_model in _CONFERENCE_MODELS` (line 528) → returns `conference_room`
unconditionally; (2) if `cucm_model in _DESK_PHONE_MODELS and has_owner is False`
(line 534) → returns `common_area`. Neither check looks at physical placement data,
device pool name patterns, or the DN's calling behavior. A 7832 in an executive's
private office (labeling CUCM description "John Smith's Conf Speakerphone") will be
typed as `conference_room`. An 8851 with no CUCM owner but placed in a break room
will be typed as `common_area` — but a model not in `_DESK_PHONE_MODELS` (e.g.,
a legacy 7942) with no owner returns `None`, which leaves the decision unresolved.
<!-- Source: recommendation_rules.py lines 508-539; devices-workspaces.md workspace types section -->

**Advisor should:** For conference model hits, check CUCM device description and
device pool name for signals like personal names, office numbers, or executive
identifiers. If found, recommend `other` (or `desk` if a user can be inferred) rather
than `conference_room`. For unowned desk phones where the model is NOT in
`_DESK_PHONE_MODELS`, the rule returns `None` and the decision remains unresolved —
flag these explicitly for human review rather than accepting the unresolved state.

**Confidence:** MEDIUM

**Signals to look for:** CUCM device description containing a personal name or office
identifier; device pool name that is location-specific rather than room-type-specific;
model not present in `_CONFERENCE_MODELS` or `_DESK_PHONE_MODELS` combined with
`has_owner = False` (these are the unresolved cases the rule drops).

### DT-USER-006: Simultaneous ring, sequential ring, and SNR cannot be migrated via admin pipeline — migration loss is unannounced

**Condition:** CUCM user has Remote Destination Profile (SNR), or simultaneousRing or
sequentialRing is configured on the CUCM line, AND the migration pipeline uses an
admin-level token.

**Why static rule fails:** The pipeline has no `SIMULTANEOUS_RING_MIGRATION` or
`SNR_MIGRATION` decision type. `recommend_snr_lossy()` in
`advisory/recommendation_rules.py:551` fires for SNR timer controls and returns
`accept_loss` with reasoning that timer controls are rarely customized — but this
reasoning does NOT address the underlying issue that the entire SNR/simultaneous ring
configuration cannot be written via admin token at all. The 6 user-only settings
listed in `self-service-call-settings.md` section 2 (simultaneousRing, sequentialRing,
priorityAlert, callNotify, anonymousCallReject, callPolicies) are exclusively at
`/telephony/config/people/me/settings/{feature}` — admin tokens get 404 on every one
of these paths. The pipeline's existing DT-USER-003 covers the general case, but the
`SNR_CONFIGURED_USERS` advisory pattern (advisory_patterns.py) fires separately and
may not be connected by the operator to the user-only token constraint. The static
"accept loss / manual" posture is insufficient when these settings existed on many
users and represent a real business continuity risk (e.g., executives relying on SNR
to reach mobile during travel).
<!-- Source: recommendation_rules.py lines 551-557; self-service-call-settings.md lines 53-64; advisory_patterns.py SNR pattern -->

**Advisor should:** When the `snr_configured_users` advisory pattern fires, do NOT
frame the recommendation as "accept loss, configure manually." Instead, explicitly
present 3 remediation paths ranked by effort:
1. **User-level OAuth integration** — Build a lightweight OAuth flow that requests
   `spark:calls_write` on behalf of each affected user and writes their SNR/simRing
   settings during the migration window. Highest effort, complete migration.
2. **Post-migration self-service** — Direct affected users to Webex User Hub to
   configure simultaneousRing/sequentialRing themselves. Low engineering effort, but
   requires user communication and follow-up.
3. **Accept loss with documented scope** — If neither option is viable, document which
   users lose which settings so post-migration support tickets can be triaged.

**Confidence:** HIGH

---

## Voicemail Greeting Migration Gap

Custom voicemail greetings (busy and no-answer) stored in Unity Connection do not transfer to Webex Calling. This is a platform limitation — Unity Connection's CUPI API exposes greeting metadata but not the audio binary in a bulk-extractable format.

### What Migrates
- Voicemail enabled/disabled state
- Ring count / number of rings before voicemail
- Voicemail-to-email settings (if supported)
- Message waiting indicator (MWI) configuration

### What Does Not Migrate
- Custom busy greeting audio
- Custom no-answer greeting audio
- Extended absence greetings
- Alternate greetings

### User Self-Service Re-Recording
After migration, users re-record greetings via:
1. **Webex App:** Settings > Calling > Voicemail > Greeting > Record
2. **Phone keypad:** Dial voicemail access number → follow prompts
3. **User Hub:** hub.webex.com > My Call Settings > Voicemail

### Admin-Path Greeting Upload API
Webex does support admin-path greeting upload if WAV files are available:
- `POST /people/{personId}/features/voicemail/actions/uploadBusyGreeting/invoke`
- `POST /people/{personId}/features/voicemail/actions/uploadNoAnswerGreeting/invoke`
- Scope: `spark-admin:people_write`
- Format: WAV, max 5 MB, multipart/form-data

This is useful if users can provide their greeting recordings (e.g., via email). The voicemail mapper creates `MISSING_DATA` decisions with `context.reason = "custom_greeting_not_extractable"` for each affected user. The advisory pattern aggregates these into a single user communication advisory.

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | 6 user-only settings list | Yes | `self-service-call-settings.md` lines 53-64; `person-call-settings-handling.md` lines 30-36 | simultaneousRing, sequentialRing, priorityAlert, callNotify, anonymousCallReject, callPolicies — exact match across both docs. |
| 2 | Workspace Basic limited to musicOnHold + DND | Yes | `devices-workspaces.md` gotcha #10 (verified 2026-03-27); CLAUDE.md known issue #6 | Under `/telephony/config/workspaces/{id}/`, only musicOnHold and doNotDisturb work on Basic. Full endpoint matrix confirms. |
| 3 | rings = cfna_timeout // 6 | Yes | `recommendation_rules.py` lines 434-441 | `rings = cfna_timeout // 6` (integer division) confirmed in source code. |
