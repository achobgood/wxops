# Location Architecture: Migration Knowledge Base

> **Audience:** Migration advisor agent (Opus) and cold-context Claude sessions looking up dissent triggers, decision context, and Webex constraints for device pool consolidation, location architecture, and E911 decisions.
> **Reading mode:** Reference. Grep by `DT-LOC-NNN` ID for dissent triggers, OR read `## Decision Framework` end-to-end when the migration-advisor agent loads this doc during analysis.
> **See also:** [Operator Runbook](../../runbooks/cucm-migration/operator-runbook.md) · [Decision Guide](../../runbooks/cucm-migration/decision-guide.md) · [Tuning Reference](../../runbooks/cucm-migration/tuning-reference.md)

## Decision Framework

### LOCATION_AMBIGUOUS

**Source:** `recommendation_rules.py` `recommend_location_ambiguous()`

Three decision paths, evaluated in order:

1. **`has_address=False` AND `dependent_device_count > 0`** --> MUST recommend `provide_address` (CRITICAL)
   - Reasoning: "Location has N devices in its pools but no street address. Webex requires an address to create a location."
   - All dependent devices will be blocked from migration without an address.
   - This check fires first, before any consolidation logic.

2. **`timezone` + `region` + `site_code` all present and match** --> recommend `consolidate`
   - Reasoning: "All partitions share timezone, region, and site code. Consolidate into a single Webex location."

3. **`timezone` + `region` match (no site_code or different site_code)** --> recommend `consolidate` (weaker confidence)
   - Reasoning: "Partitions share timezone and region. Consolidate into a single Webex location."

4. **`same_timezone=True` AND `same_region=False`** --> return `None` (no recommendation, force human review)

5. **No address, no devices** --> return `None` (genuinely ambiguous)

### When to Consolidate vs. Keep Separate

The consolidation question maps to: "Does this CUCM device pool represent a distinct physical site, or is it a logical grouping within one site?"

**Consolidate when:**
- Multiple device pools serve the same building (per-floor, per-department, per-VLAN pools)
- Pools share timezone + region + site code (strong signal for same physical site)
- The only differences between pools are MRGL, SRST reference, or codec settings (CUCM-specific, no Webex equivalent)

**Keep separate when:**
- Pools have different street addresses (different emergency dispatch locations)
- Pools are in different timezones (different business hours, different AA schedules)
- Pools represent different tenants in a shared building

**The primary location boundary in Webex is the emergency address.** If two device pools need different dispatchable addresses for E911, they must be separate Webex locations, regardless of other similarities. <!-- Source: emergency-services.md §4, RAY BAUM's Act requirements -->

### Location Consolidation Advisory (Layer 2)

**Source:** `advisory_patterns.py` `detect_location_consolidation()`

Fires when **>2 locations** share the same `(timezone, region)` tuple. Groups locations by timezone and `pre_migration_state.cucm_region_name`. Produces a `LOW` severity advisory with category `rebuild`.

Key detail: the threshold is `> 2`, not `>= 2`. Two locations sharing tz+region is common and expected. Three or more is a consolidation signal.

### E911 Migration Flag (Layer 2)

**Source:** `advisory_patterns.py` `detect_e911_migration_flag()`

Always fires, even on empty stores. Two modes:
- **Signals detected** (route patterns in E911 partitions, partition names matching E911/ELIN patterns, translation patterns with ELIN replacement): severity `HIGH`, lists affected objects, recommends separate E911 workstream.
- **No signals detected**: severity `HIGH`, warns that CER data may not be visible via AXL and administrator should verify. Still produces an advisory.

Category: `out_of_scope` in both cases. E911 migration is never part of the standard calling migration.

## Edge Cases & Exceptions

### CUCM Device Pools Are Not Physical Locations

In CUCM, device pools are the primary mechanism for assigning:
- **Date/Time Group** (timezone, NTP)
- **Region** (codec selection, bandwidth)
- **MRGL** (media resource allocation)
- **SRST Reference** (failover)
- **Calling Search Space** (routing permissions)
- **Device Mobility Group**

A single physical building commonly has 3-10 device pools for different purposes (lobby phones, exec phones, conference rooms, elevator phones, etc.). The pipeline's location mapper creates one candidate Webex location per device pool, then the advisory system flags consolidation opportunities.

### Locations with Devices but No Street Address

This is the most common migration blocker. CUCM does not require a street address on device pools. Webex requires `address1`, `city`, `state`, `postal_code`, and `country` to create a location. <!-- Source: provisioning.md line 603-608 -->

The `recommend_location_ambiguous` rule handles this: if `dependent_device_count > 0` and `has_address=False`, it always returns `provide_address`. The user must supply the address before migration can proceed. There is no workaround.

### Multiple CUCM Clusters Mapping to One Webex Org

When migrating from multiple CUCM clusters into a single Webex org:
- Each cluster's device pools are discovered independently
- The normalize phase assigns canonical IDs scoped by cluster
- Location consolidation may recommend merging device pools from different clusters that serve the same physical site
- Extension conflicts across clusters must be resolved before location mapping (different clusters may use overlapping extension ranges)

### Remote Workers Assigned to "HQ" Device Pool

CUCM commonly assigns all remote/VPN workers to a headquarters device pool for codec/region/SRST purposes, even though they are physically distributed. In Webex:
- Remote workers can be assigned to the HQ location if they share the same PSTN connectivity
- Their emergency address should be their home address (per-number E911 override), not the HQ address
- The location consolidation advisory does not distinguish remote workers from on-site users

## Real-World Patterns

### "One Building, Five Device Pools"

**CUCM:** Per-floor or per-department pools (e.g., `DP_HQ_Floor1`, `DP_HQ_Floor2`, `DP_HQ_Lobby`, `DP_HQ_Exec`, `DP_HQ_Conf`). Different MRGLs for conference bridge allocation, different CSSes for exec vs. standard routing.

**Webex:** One location. Internal dialing, voicemail, and call features are per-location. Floor differences are handled by per-number E911 addresses (RAY BAUM's Act compliance for multi-floor buildings). <!-- Source: emergency-services.md §2, per-number override via update_for_phone_number -->

### "Branch Office"

**CUCM:** One device pool, one SRST gateway, one CSS for local routing. Sometimes a second pool for analog phones (different codec region).

**Webex:** One location. The SRST gateway maps to a Webex Local Gateway trunk. The analog phones use the same location with ATA devices.

### "Data Center"

**CUCM:** Infrastructure device pools for voice gateways, IVR servers, conference bridges, media resources. No physical phones.

**Webex:** No Webex location needed. Voice gateways become Webex trunks (configured at the org level). Conference and media resources are cloud-managed. If the data center hosts a Local Gateway, the trunk is associated with the nearest user-facing location.

### "Multi-Tenant Building"

**CUCM:** Shared infrastructure with per-tenant device pools, partitions, and CSSes for call routing isolation.

**Webex:** Separate Webex locations per tenant (different emergency addresses, different PSTN connectivity, different business hours). If tenants are in different Webex orgs, this becomes a partner/VAR multi-org scenario.

## Webex Constraints

### Location Creation Requirements

Location creation requires all of the following fields: <!-- Source: provisioning.md line 603-608 -->
- `name` (max 80 characters if calling-enabled) <!-- Source: provisioning.md line 627 -->
- `time_zone` (IANA format, e.g., `America/Los_Angeles`)
- `preferred_language` (e.g., `en_us`)
- `announcement_language` (e.g., `en_us` -- must be lowercase) <!-- Source: provisioning.md line 665, gotcha #13 -->
- `address1`, `city`, `state`, `postal_code`, `country`

Optional: `address2`, `latitude`, `longitude`, `notes`.

**Location creation is two steps:** `POST /v1/locations` creates the location but does NOT enable Webex Calling. A separate `POST /v1/telephony/config/locations` enables calling. Without the second call, assigning calling-licensed users fails with "Calling flag not set". <!-- Source: provisioning.md gotcha, line 1267-1270, verified via live migration execution 2026-03-24 -->

### Calling Enablement

Calling must be enabled per-location via `api.telephony.location.enable_for_calling()`. The `announcement_language` field is required and must be lowercase (`en_us`, not `en_US`). <!-- Source: provisioning.md line 665, location-call-settings-core.md line 109-124 -->

### Internal Dialing

Configured per-location via `api.telephony.location.internal_dialing`. Controls: <!-- Source: location-call-settings-core.md line 256-299 -->
- `enable_unknown_extension_route_policy` -- route unknown extensions (2-6 digits) to a premises PBX via trunk/route group
- `unknown_extension_route_identity` -- the destination trunk or route group
- Location-level `routing_prefix` -- prefix for inter-location calls with same extension
- Location-level `outside_dial_digit` -- digit to dial for outside line (e.g., `9`)

Extension ranges are not explicitly configured per-location in Webex. Extensions are assigned per-user/workspace and validated at assignment time. The `routing_prefix` disambiguates when multiple locations use the same extension numbers.

### E911 Requirements

Every location with phones must have a validated, dispatchable emergency address. <!-- Source: emergency-services.md §4, RAY BAUM's Act checklist -->

Full compliance requires three layers:
1. **Emergency Call Notifications** (Kari's Law, U.S. Public Law 115-127): org-level email alerts when any 911 call is placed <!-- Source: emergency-services.md §1 -->
2. **Emergency Addresses** (RAY BAUM's Act): validated civic address per location, with optional per-number overrides for multi-floor/multi-building sites <!-- Source: emergency-services.md §2 -->
3. **ECBN** (Emergency Callback Number): per-person/workspace/virtual-line callback number. Extension-only users must have `LOCATION_ECBN` or `LOCATION_MEMBER_NUMBER` configured. <!-- Source: emergency-services.md §3 -->

Address validation: always call `lookup_for_location` before `add_to_location` to normalize against the PSAP database. <!-- Source: emergency-services.md §2, line 176-177 -->

### Location Deletion

Location deletion requires disabling calling first + 90s propagation wait. The sequence: <!-- Source: provisioning.md gotcha, line 1286-1295; CLAUDE.md cleanup section -->
1. Delete all location-scoped resources (virtual lines, call parks, hunt groups, call queues, schedules, trunks, devices, workspaces, users)
2. Disable calling: `wxcli location-call-settings update-location-calling LOCATION_ID --calling-enabled false`
3. Wait 90+ seconds for backend propagation
4. Delete the location: `wxcli locations delete --force LOCATION_ID`

Even after waiting, delete may return 409 for minutes to hours. Re-run cleanup to retry. <!-- Source: provisioning.md line 1295 -->

### Per-Location Limits

- Location name: max 80 characters (calling-enabled) <!-- Source: provisioning.md line 627 -->
- `user_limit`: max people at location (read-only field in `TelephonyLocation`) <!-- Source: location-call-settings-core.md line 79 -->
- Auto attendants per location: 100

## Dissent Triggers

### DT-LOC-001: Consolidation Recommended but Different Emergency Addresses

**Condition:** `LOCATION_AMBIGUOUS` recommends `consolidate` (tz + region + site_code match) BUT the device pools have different associated site addresses in CUCM or require different dispatchable addresses for E911.

**Why the static rule misses this:** `recommend_location_ambiguous` checks `timezone`, `region`, and `site_code` but does not inspect emergency address data. Two device pools can share all three attributes while serving different buildings or floors that require different PSAP dispatch addresses.

**Advisor should:** Flag that consolidation requires the same dispatchable address. If the device pools need different emergency addresses (e.g., buildings across a campus), they must remain separate Webex locations despite matching tz/region/site_code. Per-number E911 overrides can handle multi-floor scenarios within one location, but different buildings typically need different locations.

**Test:** Construct two LOCATION_AMBIGUOUS decisions with matching tz+region+site_code but different `address1` values in context. Verify the advisor dissents from the `consolidate` recommendation.

**Confidence:** HIGH

### DT-LOC-002: Address Missing but Flagged as Non-Critical

**Condition:** `LOCATION_AMBIGUOUS` with `dependent_device_count` of 1-3 AND `has_address=False`.

**Why this matters:** The static rule handles this correctly -- it always recommends `provide_address` regardless of device count. However, an advisor reviewing this might deprioritize it because "it's only 1-3 devices."

**Advisor should:** SUPPORT and ESCALATE the static rule's `provide_address` recommendation — do not override or deprioritize it. Device count is irrelevant for E911 compliance; even a single device without a validated dispatchable address is a Kari's Law / RAY BAUM's Act violation (see Reasoning below).

**Reasoning:** Even 1 device without an E911 address is a compliance violation:
- **Kari's Law** (U.S. Public Law 115-127): requires notification capability for ALL emergency calls, which requires the location to exist with proper configuration <!-- Source: emergency-services.md §1 -->
- **RAY BAUM's Act** Section 506: requires dispatchable location information for ALL 911 calls, including from enterprise locations with a single phone <!-- Source: emergency-services.md §4, RAY BAUM's Act checklist -->

A single phone at a location without a validated emergency address means a 911 call from that phone will not transmit location information to the PSAP. This is a legal compliance failure, not a quality-of-service issue.

**Test:** Construct a LOCATION_AMBIGUOUS decision with `dependent_device_count=1` and `has_address=False`. Verify the static rule returns `provide_address`. Verify the advisor supports (not overrides) the recommendation with compliance escalation language.

**Confidence:** HIGH (supporting the static rule)

### DT-LOC-003: Data Center Device Pool Creates Unnecessary Location

**Condition:** `LOCATION_AMBIGUOUS` for a device pool that contains only infrastructure devices (voice gateways, conference bridges, media resources) and no user-facing phones.

**Why the static rule may miss this:** If the device pool has `dependent_device_count > 0` (counting gateway endpoints) and `has_address=False`, the rule recommends `provide_address`. But providing an address for a data center device pool creates a Webex location that will never have users, wasting a location and potentially confusing reporting.

**Advisor should:** Check whether the dependent devices are user-facing phones or infrastructure. If all dependents are gateways/trunks/conference bridges, recommend `skip` (these become org-level trunk configurations in Webex, not location-scoped resources).

**Test:** Construct a LOCATION_AMBIGUOUS decision with `dependent_device_count=4` and context indicating all devices are gateway models. Verify the advisor recommends `skip` rather than `provide_address`.

**Confidence:** MEDIUM (depends on ability to classify device types from context)

### DT-LOC-004: Media Infrastructure Scope Removal Has Residual Location MoH Impact

**Condition:** `detect_media_resource_scope_removal` (`advisory_patterns.py:430`) fires because one or more device pools reference a Media Resource Group List — AND the migration includes more than one Webex location destination — AND custom MoH audio was in use on the CUCM MOH server(s) being decommissioned.

**Why the static rule misses this:** The `detect_media_resource_scope_removal` pattern fires `INFO` and correctly tells the operator to drop MRGLs, conference bridges, and transcoders from scope. The advisory detail (`advisory_patterns.py:458-461`) mentions "verify that Webex's default MOH audio meets your requirements (custom MOH can be uploaded per location via `wxcli announcements`)." However, this is a single-sentence action item buried in an INFO finding about scope removal. It does not flag that Webex MoH is configured independently per location (`api.telephony.location.moh`, `location-call-settings-core.md` lines 386-444), and it does not flag the voicemail PSTN access dependency (Unity Connection routes voicemail-retrieval calls through the CUCM dial plan; after cutover, those calls route through Webex). When multiple locations each had distinct custom MoH audio on the CUCM server, each Webex location must be configured individually — the scope-removal finding gives no guidance on that scope of work.

**Advisor should:** When `detect_media_resource_scope_removal` fires AND the migration has more than one location, escalate severity from INFO to MEDIUM and add two explicit action items:
1. For each Webex location, check whether the source CUCM device pool had a custom MOH audio file on the MRGL's MOH server. If yes, upload the audio to that Webex location via `wxcli announcements upload` and configure it with `wxcli location-settings update-music-on-hold --greeting CUSTOM`. Do this before cutover — the default system greeting plays immediately after the location is created.
2. Verify voicemail pilot DN routing. If Unity Connection is being decommissioned alongside the media infrastructure, the per-location voice portal number (`wxcli location-voicemail show-voice-portal`) must be validated before cutover. Voicemail-retrieval calls that previously routed through CUCM → Unity Connection must now resolve through the Webex dial plan.

**Signals to look for:** More than one location in the migration plan AND any device pool's MRGL name contains "MOH" or "MusicOnHold". Also: any voicemail pilot object whose `pre_migration_state` references the same server as an MRGL component (indicates Unity Connection and MOH server are co-located).

**Confidence:** MEDIUM — the MoH upload requirement is grounded in `location-call-settings-core.md` lines 386-444 (`LocationMoHApi`, `SYSTEM`/`CUSTOM` enum, `wxcli location-settings update-music-on-hold`). The voicemail cutover dependency is inferred from the architecture (Unity Connection PSTN routing through CUCM dial plan) but not explicitly documented in a reference doc.

---

### DT-LOC-005: Location Consolidation Forces ERL Remap as Hard Prerequisite

**Condition:** `detect_location_consolidation` (`advisory_patterns.py:225`) recommends collapsing multiple CUCM device pools into fewer Webex locations — AND `detect_e911_migration_flag` (`advisory_patterns.py:1066`) has also fired (E911/CER signals detected or the always-fires warning is present).

**Why the static rule misses this:** `detect_e911_migration_flag` fires independently of `detect_location_consolidation`. Its recommendation is to "initiate a separate E911 workstream in parallel" (`advisory_patterns.py:1104-1110`). This is correct in isolation, but it treats E911 as a parallel track that can proceed independently. The cross-pattern interaction it misses: when location consolidation reduces N device pools to M Webex locations (M < N), every CER Emergency Response Location (ERL) that was mapped to one of the consolidated device pools must be remapped to the consolidated Webex location. In Webex, emergency addresses are location-scoped (`EmergencyAddressApi.add_to_location`, `emergency-services.md` lines 138-163); per-number overrides exist (`update_for_phone_number`, `emergency-services.md` lines 221-222) but require explicit assignment per phone number. The ERL-to-location mapping in CER cannot be assumed to survive consolidation — it must be explicitly re-verified and re-configured.

**Advisor should:** When both patterns fire in the same migration run, add a cross-pattern finding that blocks the consolidation recommendation from being auto-accepted until the E911 workstream has explicitly mapped each consolidated location's emergency address. Specifically:
1. For each proposed consolidation (N pools → 1 Webex location), enumerate the distinct CER ERL names that were assigned to the source device pools.
2. If those ERLs had different civic addresses or different ELIN ranges, the consolidation creates a single Webex location that can only carry one validated emergency address as its default. Any phones that need a different dispatchable address must be assigned per-number overrides.
3. The E911 workstream must complete the `lookup_for_location` → `add_to_location` sequence for the consolidated location BEFORE the location is used for cutover. This is a hard prerequisite, not a follow-up task.

**Signals to look for:** Both `location_consolidation` and `e911_migration_flag` present in the same advisory run. MRGL names or partition names containing "ERL", "ELIN", or "CER". More than one distinct address value in the source device pools that are being consolidated.

**Confidence:** HIGH — grounded in `emergency-services.md` lines 119-122 (location-level vs. phone-number-level emergency addresses), lines 595-596 (multi-building/multi-floor per-number override requirement), and `advisory_patterns.py:1066` (`detect_e911_migration_flag` always-fires design). The cross-pattern interaction is a structural consequence of two verified independent behaviors.

---

### DT-LOC-006: Location Architecture for Workspace Tier Affects Location-Level Call Recording

**Condition:** `recommend_workspace_license_tier` (`recommendation_rules.py:103`) recommends `"basic"` for one or more workspaces at a given location — AND the location has a call recording setting enabled (`/telephony/config/locations/{locationId}/callRecording`) — OR — the `detect_recording_enabled_users` pattern (`advisory_patterns.py:1143`) fires for users at the same location.

**Why the static rule misses this:** `recommend_workspace_license_tier` (`recommendation_rules.py:103-118`) checks `features_detected` against `_PROFESSIONAL_FEATURES`. The set `_PROFESSIONAL_FEATURES` includes `"callRecording"` (`recommendation_rules.py:18`), so a workspace with explicit call recording configured WILL be recommended as Professional. However, the rule operates per-workspace from the CUCM phone's feature inventory — it cannot see the location-level call recording configuration that would be applied to ALL workspaces at that location once the Webex location is provisioned. A workspace that had no individual CUCM recording setting may still inherit location-level Webex call recording after migration, requiring a Professional license. Additionally, Basic workspaces return 405 on the `/telephony/config/workspaces/{id}/callRecording` endpoint (`devices-workspaces.md` lines 1374, 1352). A location with a mix of Professional and Basic workspaces cannot apply a blanket location-level call recording policy — the Basic workspaces silently fail to record.

**Advisor should:** When any workspaces at a location are recommended as `"basic"` AND the location's recording pattern (from `detect_recording_enabled_users`) or location-level recording config indicates recording is required, flag this as a location-architecture concern:
1. Basic workspaces cannot participate in `/telephony/config/workspaces/{id}/callRecording` (returns 405 "Invalid Professional Place"). Source: `devices-workspaces.md` lines 1352, 1374.
2. If compliance recording (FINRA, MiFID II, HIPAA) applies to this location, ALL workspaces at that location should be provisioned as Professional — not only those that had individual CUCM recording flags.
3. Upgrade the recommendation from `"basic"` to `"professional"` for workspaces at recording-required locations, and document the reason as location-level compliance recording rather than per-workspace feature detection.

**Signals to look for:** `recommend_workspace_license_tier` returning `"basic"` for workspaces at a location where `detect_recording_enabled_users` also fired. Any location where a subset of phones had `recordingFlag != "Call Recording Disabled"` and another subset had `recordingFlag == "Call Recording Disabled"` — the mixed state indicates the `basic` recommendation may apply to the non-recording phones, which is correct per-device but wrong in the location context.

**Confidence:** MEDIUM — the 405 behavior for Basic workspace call recording is grounded in `devices-workspaces.md` lines 1352, 1374 (endpoint access by license tier table). The location-level recording inheritance logic is inferred from the location-architecture design, not from an explicit reference doc statement.

---

### dt-loc-e911

**Title:** Location ECBN and emergency-call-notification — "user's assigned location" is wrong for hoteling / hotdesk / remote topologies

**Condition:** A location-scoped E911 decision (`E911_LOCATION_MISMATCH` or the location half of `E911_ECBN_AMBIGUOUS`) fires, OR the operator is reviewing which phone number to designate as the location-level ECBN source for users without DIDs.

**Why static rule fails:** The `EcbnMapper` and `e911_readiness` advisory pattern rely on `user_in_location` cross-refs built from CUCM device pool → location lookup. That mapping is correct for traditional fixed-seat deployments, but it silently breaks on three topologies that are now common:

1. **Hoteling / hot desk users** — the "user's assigned location" is the hoteling pool controller, not the user's physical location on any given day. The ECBN and dispatch address must correspond to the physical seat, not the pool. Webex Calling supports this via RedSky or per-device location overrides; the static mapper cannot tell which users need it.
2. **Remote / work-from-home users** — the CUCM device pool is the corporate HQ (because that's where the phone was provisioned originally), but the phone now lives at the user's home address. Dispatching EMS to the HQ address on a 911 call is both wrong and a regulatory violation under RAY BAUM's Act.
3. **Multi-building or multi-floor campuses** — Webex location-level emergency addresses are a single address per location. Any campus larger than one building or taller than ~7000 sq ft per floor needs per-number or per-device address overrides. `emergency-services.md` lines 595–596 require the per-number override path for multi-building campuses; a location-level-only ECBN design silently under-serves these.

**Advisor should:** When `E911_LOCATION_MISMATCH` fires, before accepting the mapper's location-ECBN pick, ask:
1. Are any devices at this location actually hoteling/hotdesk phones? (Signal: device name contains `hotel`, `hotdesk`, `guest`, or the `DeviceProfile` / EM references are non-empty.)
2. Are any users at this location remote workers? (Signal: user `homePhoneNumber` or `telephoneNumber` fields match an E.164 outside the location's area code.)
3. Is the location a single building under ~7000 sq ft per floor? (Signal: customer provides building floorplan; otherwise ask explicitly.)

If any signal fires, recommend either (a) integrating RedSky Horizon / dynamic-location provider and setting `e911.redsky_enabled = true` in config, (b) per-number/per-device emergency address overrides during execution, or (c) escalating to a customer-led E911 workshop before the cut. Also confirm that `e911.notification_email` is set to a monitored distribution — a failed 911 notification cannot be backfilled after the fact.

**Confidence:** HIGH — grounded in `emergency-services.md` (Kari's Law + RAY BAUM's Act requirements) and `advisory_patterns.py:1066` (`detect_e911_migration_flag` always-fires design). The three topology signals are industry-standard concerns documented in RAY BAUM's Act compliance guidance.

<!-- Source: emergency-services.md lines 17, 581-609, 595-596; ecbn_mapper.py LOCATION_ECBN selection path; advisory_patterns.py e911 pattern -->

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | Location creation requires valid street address | Yes | `provisioning.md` lines 603-608 | `address1`, `city`, `state`, `postal_code`, `country` listed as required parameters for `locations.create()`. |
| 2 | E911 compliance (Kari's Law + RAY BAUM's Act) | Yes | `emergency-services.md` line 17, lines 581-609 | Three interlocking layers: Emergency Call Notifications (Kari's Law), Emergency Addresses (RAY BAUM's Act), and ECBN. Full compliance checklist documented. |
| 3 | 90s propagation wait for calling disable | Yes | `provisioning.md` lines 1286-1295 (verified via stress test 2026-03-25); CLAUDE.md cleanup section line 240, 249 | "Wait 90+ seconds for the backend to propagate the change" confirmed in both sources. |
