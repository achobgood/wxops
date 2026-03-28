# Location Architecture: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

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

A single physical building commonly has 3-10 device pools for different purposes (lobby phones, exec phones, conference rooms, elevator phones, etc.). The pipeline's location mapper creates one candidate Webex location per device pool, then the advisory system flags consolidation opportunities. <!-- From training, needs verification -->

### Locations with Devices but No Street Address

This is the most common migration blocker. CUCM does not require a street address on device pools. Webex requires `address1`, `city`, `state`, `postal_code`, and `country` to create a location. <!-- Source: provisioning.md line 603-608 -->

The `recommend_location_ambiguous` rule handles this: if `dependent_device_count > 0` and `has_address=False`, it always returns `provide_address`. The user must supply the address before migration can proceed. There is no workaround.

### Multiple CUCM Clusters Mapping to One Webex Org

When migrating from multiple CUCM clusters into a single Webex org:
- Each cluster's device pools are discovered independently
- The normalize phase assigns canonical IDs scoped by cluster
- Location consolidation may recommend merging device pools from different clusters that serve the same physical site
- Extension conflicts across clusters must be resolved before location mapping (different clusters may use overlapping extension ranges) <!-- From training, needs verification -->

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

**Webex:** Separate Webex locations per tenant (different emergency addresses, different PSTN connectivity, different business hours). If tenants are in different Webex orgs, this becomes a partner/VAR multi-org scenario. <!-- From training, needs verification -->

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
- Auto attendants per location: 100 <!-- From training, needs verification -->

## Dissent Triggers

### DT-LOC-001: Consolidation Recommended but Different Emergency Addresses

**Condition:** `LOCATION_AMBIGUOUS` recommends `consolidate` (tz + region + site_code match) BUT the device pools have different associated site addresses in CUCM or require different dispatchable addresses for E911.

**Why the static rule misses this:** `recommend_location_ambiguous` checks `timezone`, `region`, and `site_code` but does not inspect emergency address data. Two device pools can share all three attributes while serving different buildings or floors that require different PSAP dispatch addresses.

**Advisor should:** Flag that consolidation requires the same dispatchable address. If the device pools need different emergency addresses (e.g., buildings across a campus), they must remain separate Webex locations despite matching tz/region/site_code. Per-number E911 overrides can handle multi-floor scenarios within one location, but different buildings typically need different locations.

**Test:** Construct two LOCATION_AMBIGUOUS decisions with matching tz+region+site_code but different `address1` values in context. Verify the advisor dissents from the `consolidate` recommendation.

**Confidence:** HIGH

### DT-LOC-002: Address Missing but Flagged as Non-Critical

**Condition:** `LOCATION_AMBIGUOUS` with `dependent_device_count` of 1-3 AND `has_address=False`.

**Why this matters:** The static rule handles this correctly -- it always recommends `provide_address` regardless of device count. However, an advisor reviewing this might deprioritize it because "it's only 1-3 devices." The advisor should SUPPORT and ESCALATE the static rule's recommendation.

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
