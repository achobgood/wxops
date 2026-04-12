# Trunk & PSTN: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

> **Audience:** Migration advisor agent (Opus) and cold-context Claude sessions looking up dissent triggers, decision context, and Webex constraints for trunk topology, LGW vs CCPP, and CPN transformation decisions.
> **Reading mode:** Reference. Grep by `DT-TRUNK-NNN` ID for dissent triggers, OR read `## Decision Framework` end-to-end when the migration-advisor agent loads this doc during analysis.
> **See also:** [Operator Runbook](../../runbooks/cucm-migration/operator-runbook.md) · [Decision Guide](../../runbooks/cucm-migration/decision-guide.md) · [Tuning Reference](../../runbooks/cucm-migration/tuning-reference.md)

## Decision Framework

### Local Gateway vs Cloud Connected PSTN vs Premises-based PSTN

Three PSTN connection types exist in Webex Calling. The choice determines the entire routing architecture.
<!-- Source: call-routing.md §PSTN Configuration, PSTNType enum -->

| Type | API Value | When to Use | API-Configurable? |
|------|-----------|-------------|-------------------|
| **Local Gateway** | `LOCAL_GATEWAY` | Customer owns SBC/CUBE on-premises, manages their own PSTN circuits (SIP trunks, PRI via CUBE). Preserves existing carrier relationships. Required when survivability (SRST) is needed. | Yes |
| **Cloud Connected PSTN (CCPP)** | `NON_INTEGRATED_CCP` or `INTEGRATED_CCP` | Cisco-managed PSTN via certified CCP partners. No on-prem equipment needed. Pure cloud deployment. | Non-integrated: Yes. Integrated: Control Hub only. |
| **Cisco Calling Plan** | `CISCO_PSTN` | Cisco is the PSTN provider. Numbers ordered/ported through Cisco. | Control Hub only |
| **Premises-based PSTN** | Used with Dedicated Instance | For Webex Calling Dedicated Instance deployments where PSTN connects to on-prem infrastructure via route lists. | Via route list configuration |

**Migration decision logic** (from `detect_pstn_connection_type()` in `advisory_patterns.py`, Pattern 13):

1. **No trunks detected** --> Cloud Connected PSTN. Pure cloud, no equipment to reuse.
2. **SBC name/address/type keywords found** (regex: `cube|audiocodes|ribbon|oracle|sbc|session.?border|mediant|gateway`) --> Local Gateway. Reuse existing SBC as Webex Local Gateway.
3. **PRI/gateway objects detected** --> Local Gateway. PRI circuits require local hardware. Convert to CUBE as Webex Local Gateway.
4. **Carrier SIP trunks + SRST present** --> Local Gateway. Survivability requirement means a local SBC is needed even for pure SIP.
5. **Carrier SIP trunks, no SRST** --> Cloud Connected PSTN if carrier is a Webex CCPP partner, otherwise Local Gateway with a Webex-registered SBC.

### When Multiple CUCM Trunks Should Become One Webex Trunk

**Consolidation logic** (from `detect_trunk_destination_consolidation()` in `advisory_patterns.py`, Pattern 8):

CUCM commonly uses multiple trunks to the same SBC/destination for call capacity distribution and failover. The pattern groups trunks by first destination address (`addressIpv4`, `addressIpv6`, or `host`). When 2+ trunks share the same destination, it recommends consolidating into one Webex trunk because Webex trunks support multiple destination addresses in a priority/weight configuration natively.

**Keep separate when:**
- Trunks serve genuinely different routing purposes (e.g., one for outbound PSTN, one for inter-cluster)
- Different SIP profiles or transformation requirements per trunk
- Different carriers at different sites

### Route Group Design

Route groups provide two routing strategies via the `priority` field on each trunk member:
<!-- Source: call-routing.md §Route Groups, RGTrunk data model -->

- **Priority-based failover**: Assign different priority values (1 = primary, 2 = backup). Calls go to priority 1 trunk; if unavailable, fall to priority 2.
- **Equal-weight load balancing**: Assign the same priority value to multiple trunks. Calls are distributed across trunks with equal priority.

A single route group can combine both strategies (e.g., two primary trunks with priority 1 for load balancing, one backup trunk with priority 2 for failover).

## Edge Cases & Exceptions

### CUCM Trunks with Complex Transformation Masks

CUCM applies calling/called party number transformations in a chain across up to 5 levels (route pattern, route list, route group, trunk, gateway). Webex uses flat caller ID per user/location -- no chained transformation equivalent.
<!-- Source: detect_cpn_transformation_chain() in advisory_patterns.py, Pattern 12 -->

The CPN transformation chain detector checks for:
- `callingPartyTransformationMask` / `calling_transform_mask` on route patterns and trunks --> caller ID masking
- `calledPartyTransformationMask` / `called_transform_mask` on route patterns and trunks --> called party manipulation
- `prefixDigitsOut` / `prefix_digits_out` on route patterns --> digit prefixing

**Multi-level chains** (both route patterns AND trunks have transforms) are the highest risk. CUCM CSS-level calling party transformation fields are NOT extracted by the discovery pipeline -- manual review required if used.

**Webex equivalent:** Configure caller ID at user or location level. Verify location dialing settings handle called party manipulation natively. Webex translation patterns provide limited digit manipulation (matching pattern --> replacement pattern), but only for outbound calls.

### Inter-Cluster Trunks (CUCM-to-CUCM)

Inter-cluster trunks in CUCM (ICT, SIP ICT) connect separate CUCM clusters. These have no direct Webex equivalent because Webex is a single-cluster cloud platform. During migration:
- If both clusters are migrating: eliminate the ICT entirely -- all users will be in the same Webex org.
- If only one cluster is migrating: convert the ICT to a Local Gateway trunk for calls between Webex and the remaining CUCM cluster.
<!-- From training, needs verification -->

### H.323 Trunks

Webex Calling is SIP-only. H.323 trunks from CUCM cannot be migrated directly. The gateway or endpoint must be replaced with SIP-capable equipment, or a SIP-to-H.323 interworking gateway (like CUBE) must be placed in the path.
<!-- From training, needs verification -->

### MGCP Gateways

MGCP gateways (e.g., Cisco 28xx, 38xx, VG series in MGCP mode) cannot register with Webex directly. They must be converted to SIP mode (CUBE/SIP gateway) or replaced with SIP-capable gateways. The `detect_pstn_connection_type()` pattern detects gateway objects and recommends Local Gateway with CUBE conversion.
<!-- From training, needs verification -->

### Transformation Patterns in Webex

Webex translation patterns are simpler than CUCM transformations:
<!-- Source: call-routing.md §Translation Patterns -->

- Outbound calls only
- Two levels: organization-level or location-level
- Simple matching pattern --> replacement pattern (no chained transforms)
- E.164 replacement patterns cannot contain `X` wildcards (gotcha #1 in call-routing.md)
- Non-E.164 patterns can use `X` for digit manipulation (e.g., `9XXX` --> `XXX` to strip prefix)

`detect_transformation_patterns()` (Pattern 19) flags all CUCM calling/called party transformation patterns for manual review. Each requires mapping to Webex's flat caller ID model or translation patterns.

## Real-World Patterns

### Single SBC
One CUBE on-premises --> one Webex trunk (REGISTERING type) + one route group (single member) + dial plan pointing to the route group. Location PSTN connection set to Local Gateway with the trunk or route group as the route choice.

### Geo-Redundant SBC
Two CUBEs at different sites --> two Webex trunks (one per location) in one route group with priority-based failover (primary=1, backup=2). Single dial plan points to the route group.

### Carrier Per Site
Different PSTN carriers at each site --> separate trunk per site, each location's PSTN connection configured independently. May use individual dial plans per site or a shared dial plan with a route group if the carriers serve the same number ranges.

### Centralized Breakout
All PSTN traffic routes through one data center --> single trunk (or route group with redundant trunks) at the central location. All locations' PSTN connections point to the same trunk/route group. Dial plan is org-wide so this works naturally.

### Hybrid Migration (Coexistence)
CUCM and Webex running in parallel during migration --> Local Gateway trunk between Webex and CUCM (via CUBE). CUCM-side users reached via dial plan patterns pointing to the trunk. As users migrate, patterns are adjusted. This is the inter-cluster trunk replacement pattern.
<!-- From training, needs verification -->

## Webex Constraints

### Webex Trunk Types

Two trunk types exist in Webex Calling, determined at creation time and immutable after:
<!-- Source: call-routing.md §Trunks, TrunkType enum -->

| Type | API Value | Use Case | Authentication | Required Fields |
|------|-----------|----------|---------------|-----------------|
| **Registering** | `REGISTERING` | Cisco CUBE Local Gateway. SBC registers with Webex cloud. | Password-based (SIP registration) | `name`, `locationId`, `password` |
| **Certificate-based** | `CERTIFICATE_BASED` | Third-party SBCs: AudioCodes, Ribbon, Oracle ACME, Cisco UBE. Uses mutual TLS. | mTLS certificate | `name`, `locationId`, `password`, `address` (FQDN/SRV), `domain`, `port`, `maxConcurrentCalls` |

**Immutable after creation:** `trunkType`, `locationId`, `deviceType`. Must delete and recreate to change these.
<!-- Source: call-routing.md §Update Trunk limitation -->

### Limits & Constraints

1. **Route groups max 10 trunks** -- a single route group can contain up to 10 trunks from different locations.
   <!-- Source: call-routing.md line 58: "A Route Group bundles up to 10 trunks" and line 820: "up to 10, from different locations" -->

2. **Dial plans are org-wide** -- dial plans apply globally to all users regardless of location. There is no per-location dial plan scoping (unlike CUCM partitions/CSSes).
   <!-- Source: call-routing.md line 55: "Dial Plans are configured globally (org-wide, not per-location)" -->

3. **Translation patterns limited to digit manipulation** -- matching pattern to replacement pattern, outbound only, org-level or location-level. No equivalent to CUCM's 5-level transformation chain.
   <!-- Source: call-routing.md §Translation Patterns -->

4. **Trunk type and location immutable after creation** -- cannot change `trunkType`, `locationId`, or `deviceType` via update. Must delete and recreate.
   <!-- Source: call-routing.md §Update Trunk -->

5. **Only LOCAL_GATEWAY and NON_INTEGRATED_CCP configurable via API** -- INTEGRATED_CCP and CISCO_PSTN must be configured through Control Hub UI.
   <!-- Source: call-routing.md line 1621 -->

6. **Dial plans require an existing route choice** -- cannot create a standalone dial plan without a trunk or route group reference.
   <!-- Source: call-routing.md gotcha #2 -->

7. **No H.323 trunk support** -- Webex is SIP-only. All trunk types (REGISTERING, CERTIFICATE_BASED) use SIP.
   <!-- From training, needs verification. call-routing.md TrunkType enum only has REGISTERING and CERTIFICATE_BASED, both SIP. No H.323 type exists. -->

8. **No MGCP gateway support** -- Webex trunks connect to SBCs/local gateways via SIP. No MGCP control protocol equivalent.
   <!-- From training, needs verification -->

## Dissent Triggers

### DT-TRUNK-001: Trunk consolidation recommended but trunks serve different routing purposes

- **Condition:** `trunk_destination_consolidation` pattern fires AND 2+ trunks point to the same destination address BUT trunk names suggest different functions (e.g., one named `*-PSTN-*` and another named `*-INTERCLUSTER-*` or `*-VM-*`)
- **Why static fires incorrectly:** The pattern matches on destination IP/hostname only. Two trunks to the same SBC that serve different routing purposes (outbound PSTN vs. voicemail vs. inter-cluster) would be flagged for consolidation when they should remain separate in the Webex routing design.
- **Advisor should:** Inspect trunk names for function keywords. Check if the trunks have different SIP profiles, different called-party transformations, or appear in different route groups. Ask the admin whether the SBC uses trunk-specific routing profiles (e.g., different SIP trunk security profiles or SIP route patterns on the SBC side).
- **Confidence:** MEDIUM

### DT-TRUNK-002: CCPSTN recommended but environment has SBC with custom features

- **Condition:** `pstn_connection_type` pattern recommends Cloud Connected PSTN (pure SIP trunks, no SBC name/type indicators) BUT `cpn_transformation_chain` pattern also fires showing calling/called party transformation masks on the same trunks
- **Why static fires incorrectly:** The PSTN type detector looks for SBC name/type keywords (`cube`, `audiocodes`, `ribbon`, `oracle`, `sbc`, `session.border`, `mediant`, `gateway`). A carrier SIP trunk with a generic name (e.g., `Carrier-SIP-01`) that has complex transformation masks configured at the CUCM route pattern or trunk level won't trigger the SBC detection. The transformations suggest the deployment relies on carrier-specific digit manipulation that may not be available in a CCPP model.
- **Advisor should:** Cross-reference the transformation masks with the trunk. If `callingPartyTransformationMask` or `calledPartyTransformationMask` is set on the trunk or its route patterns, flag that these transformations suggest carrier-specific requirements. Ask whether the carrier requires specific ANI/DNIS manipulation that would need an SBC (making Local Gateway the better choice even without an existing SBC).
- **Confidence:** LOW

### DT-TRUNK-003: Single trunk recommended but CUCM uses route list for PSTN redundancy

- **Condition:** `trunk_destination_consolidation` fires AND the consolidated trunks appear in a CUCM route list with ordered route group members
- **Why static fires incorrectly:** CUCM route lists chain route groups in a specific order for overflow/failover across different trunk groups. Consolidating to a single trunk loses the multi-tier failover that the route list provided.
- **Advisor should:** Check if the CUCM route list has multiple route groups (not just multiple trunks in one group). If so, recommend a Webex route group with priority-based trunks to preserve the failover hierarchy rather than consolidating to one trunk.
- **Confidence:** MEDIUM

### DT-TRUNK-004: Trunk type (REGISTERING vs CERTIFICATE_BASED) cannot be determined from trunk name or address

- **Condition:** `detect_trunk_type_selection` (`advisory_patterns.py:1550`) fires AND the flagged trunk name matches neither `_CISCO_CUBE_PATTERNS` (e.g., `cube`, `isr`, `csr`, `c8xxx`, `ios-xe`) nor `_THIRD_PARTY_SBC_PATTERNS` (e.g., `audiocodes`, `ribbon`, `oracle`, `mediant`, `sonus`) — resulting in a trunk in `needs_type_decision`. Typical examples: `Main_SIP_Trunk_Voice`, `SBC_Voice_01`, `PSTN_Primary`, `Voice_Trunk_HQ`.
- **Why static fires correctly but is insufficient:** The regex correctly identifies that it cannot classify the trunk — the finding is accurate. The problem is what happens next. Without the advisor's explicit framing, an operator might guess based on IP address (wrong), vendor of another trunk in the same environment (wrong), or the word "SBC" in an internal name that refers to a different device (wrong). The static rule emits `severity=CRITICAL` but does not explain WHY the choice is irreversible. Webex trunk type is IMMUTABLE after creation (`call-routing.md:584`: "You cannot change `trunk_type`, `location_id`, or `device_type` after creation. To change these properties, you must delete and recreate the trunk"). Delete + recreate during a live cutover tears down the route-group/route-list entries that reference the trunk, causing a calling outage that may take 15-30 minutes to restore.
- **Advisor should:** For each unclassified trunk, require the operator to confirm the exact hardware model that terminates it. Provide the decision rule explicitly: REGISTERING = Cisco IOS-XE CUBE (ISR 4000/4400, CSR 1000v, C8300/C8500, Catalyst 8000v); CERTIFICATE_BASED = third-party SBC (AudioCodes, Ribbon/GENBAND, Oracle/Acme Packet, Sonus/SWe Lite, Avaya SBC). Do not allow the migration to proceed to the plan phase until every trunk in `needs_type_decision` has been manually classified. Escalate to `severity=CRITICAL` with a blocking flag if the static rule did not already do so.
- **Confidence:** HIGH

### DT-TRUNK-005: ICTs converted to Local Gateway during coexistence require a cascade of decisions the static rule does not surface

- **Condition:** `detect_intercluster_trunks` (`advisory_patterns.py:1625`) fires AND one or more ICTs receive a disposition of "convert to Local Gateway" (coexistence window — one cluster migrates while the other stays on CUCM). The static `detect_intercluster_trunks` finding lists ICTs and asks for a per-trunk disposition but does not analyze the downstream decisions that a "convert" disposition triggers.
- **Why static fires correctly but is insufficient:** The intercluster trunk pattern correctly identifies the ICTs and requests a disposition decision. However, converting an ICT to a Local Gateway trunk introduces at least two cascading decisions that the static rule does not surface: (1) The converted trunk still needs a REGISTERING vs CERTIFICATE_BASED type decision (see DT-TRUNK-004) — an ICT was a CUCM-internal protocol and carries no SBC vendor signal, so it will always land in `needs_type_decision`. (2) ICT-derived Local Gateway trunks carry on-net inter-cluster calls (DIDs for remote-cluster users, internal extensions, EMCC) — these require different DID ranges and CSS/partition treatment than PSTN trunks. If the operator configures the converted ICT trunk with the same dial plan as the PSTN trunk, on-net calls will be routed to the PSTN gateway and hairpin back, incurring carrier charges and adding latency. The static rule surfaces neither the trunk-type cascade nor the routing-scope risk.
- **Advisor should:** When `detect_intercluster_trunks` fires and any trunk disposition is "convert to Local Gateway", cross-reference with `detect_trunk_type_selection` to confirm those trunks are also in `needs_type_decision`. If they are (which they always will be — no ICT will have a matching CUBE or SBC regex), present both findings together as a compound decision: trunk disposition + trunk type + dial plan scoping. Explicitly warn that the dial patterns in the route group for this trunk must be restricted to the remote-cluster DN range and must NOT overlap with the org-wide PSTN dial plan.
- **Confidence:** HIGH

### DT-TRUNK-006: Post-conversion SIP trunks from MGCP/H.323 still need LGW vs CCPP and REGISTERING vs CERTIFICATE_BASED decisions

- **Condition:** `detect_legacy_gateway_protocols` (`advisory_patterns.py:1687`) fires AND identifies one or more MGCP gateways (VG224, VG400, FXS/FXO analog gateways) or H.323 devices that will be converted to SIP trunks before Webex provisioning.
- **Why static fires correctly but is insufficient:** The `detect_legacy_gateway_protocols` pattern correctly identifies MGCP and H.323 objects and correctly states that conversion to SIP must happen before Webex trunk provisioning (`call-routing.md:584`). The gap is that the recommendation stops at "convert to SIP" without analyzing what the resulting SIP trunk will look like. A converted MGCP VG400 running IOS-XE CUBE becomes a REGISTERING trunk (Local Gateway). A converted H.323 gatekeeper that is replaced with an AudioCodes SBC becomes a CERTIFICATE_BASED trunk. A carrier SIP trunk that replaces an H.323 gatekeeper for PSTN calling may use either Local Gateway or Cloud Connected PSTN depending on whether an SBC remains in the path. The static rule emits `severity=HIGH` and a "convert before provisioning" recommendation but leaves all three of these classification decisions implicit — meaning the operator who reads the finding may believe the work is done once they finish the protocol conversion, unaware that two more decision points remain before the Webex trunk can be created.
- **Advisor should:** For each MGCP or H.323 object flagged by `detect_legacy_gateway_protocols`, project forward to the expected post-conversion topology and surface the remaining decisions explicitly: (1) After conversion, will the device run IOS-XE CUBE → flag for REGISTERING type (DT-TRUNK-004). (2) After conversion, will a third-party SBC handle the call leg → flag for CERTIFICATE_BASED type (DT-TRUNK-004). (3) After conversion, is the resulting connection pure carrier SIP with no on-premises SBC → flag for `pstn_connection_type` decision (DT-TRUNK-002: LGW vs CCPP). Present these as a sequenced checklist: "Before provisioning this trunk in Webex, verify: (a) protocol conversion is complete, (b) trunk type has been determined (REGISTERING vs CERTIFICATE_BASED), (c) PSTN connection type has been determined (LGW vs CCPP)."
- **Confidence:** HIGH

## Route List Complexity

<!-- Added 2026-04-12 for advisory Pattern 32 -->

### The Constraint: One Route Group Per Webex Route List

CUCM route lists are multi-member ordered lists — a single route list can contain multiple route groups (e.g., `US-West-RG` as primary, `US-East-RG` as backup). This ordered membership is the mechanism for geographic PSTN failover: when the first route group's trunks are unavailable, CUCM tries the next member in sequence. Webex route lists bind to exactly one route group (`routeGroupId` is a required singular field in the POST body — see `docs/reference/call-routing.md` §Route Lists). There is no concept of ordered failover across route groups at the route list level.

### Split vs Flatten: When Each Applies

When a CUCM route list has N route group members, the migration mapper produces a FEATURE_APPROXIMATION decision with three options:

| Option | Result | When to Use |
|--------|--------|-------------|
| **Split** | N Webex route lists, one per route group member | Geographic PSTN failover is a live requirement. Each site's trunks must remain independently routable. The customer's dial plan already distinguishes inbound DID ranges by region. |
| **Flatten** | 1 Webex route list using the first (primary) route group | The secondary route groups were CUCM-era redundancy that the customer is retiring. All calls will use a single carrier/SBC post-migration. SRST is not a concern (cloud survivability handles it). |
| **Skip** | No Webex route list created | The route list was an engineering artifact — its dial patterns are being removed, its number range is being decommissioned, or it was part of an over-engineered dial plan that simplifies away on Webex. |

**Split is the safer default for Dedicated Instance deployments.** Webex Calling Dedicated Instance requires route lists to bind phone numbers to the correct route group for cloud PSTN connectivity. Flattening loses which DIDs are reachable via which trunk, which can prevent Dedicated Instance PSTN calls from routing correctly. When in doubt with a DI topology, split.

### Concrete Example

```
CUCM route list: US-Failover-RL
  Member 1 (primary):  US-West-RG  → SJ-GW trunk (priority 1)
  Member 2 (backup):   US-East-RG  → NY-GW trunk (priority 1)

Split result (2 Webex route lists):
  US-Failover-RL-West  → US-West-RG  (numbers: +14085551000–+14085551999)
  US-Failover-RL-East  → US-East-RG  (numbers: +12125551000–+12125551999)

Flatten result (1 Webex route list):
  US-Failover-RL       → US-West-RG  (all numbers: both ranges)
  [US-East-RG no longer in routing path]
```

The split result preserves regional DID bindings. Dial plans that previously pointed at `US-Failover-RL` now must be updated to reference the correct split list — or if Webex dial plans cannot reference route lists directly (RouteType enum only exposes `ROUTE_GROUP` and `TRUNK`), the route groups remain the dial-plan target and the route lists serve as number-binding containers for Dedicated Instance connectivity.

### Advisory Pattern

`detect_route_list_complexity` (Pattern 32, `advisory_patterns.py`) fires as a MEDIUM/HIGH cross-cutting advisory when any route list in the store has multiple route group members. HIGH fires when every route list is multi-member (entire routing layer needs decisions). MEDIUM fires when a mix of single-member and multi-member route lists exists. The advisory quantifies total Webex route list count under each option so the operator understands scope before reaching individual per-list FEATURE_APPROXIMATION decisions in the review queue.

## Route Lists

**Prior assumption was wrong:** The pipeline previously assumed Webex Calling had no route list support. Webex has full route list CRUD at `/telephony/config/premisePstn/routeLists`.

CUCM route lists wrap multiple route groups in priority order for PSTN failover. Webex route lists bind to exactly ONE route group (no multi-member failover within a single route list).

**Migration mapping:**
- CUCM route list with 1 route group → direct 1:1 mapping to Webex route list
- CUCM route list with 2+ route groups → FEATURE_APPROXIMATION decision. Options:
  1. Split into N route lists (one per route group) — preserves all paths but loses priority ordering
  2. Use first route group only — preserves primary path, loses failover
  3. Skip route list — route patterns point to route groups directly

**Dependency chain:** Trunk → Route Group → Route List → Dial Plan

**Webex RouteType constraint:** Dial plans reference targets by RouteType enum which includes `ROUTE_GROUP` and `TRUNK`. Whether `ROUTE_LIST` is a valid RouteType needs live API verification. If not, route lists exist as standalone resources but cannot be dial plan targets — they serve only as an organizational wrapper.

### Dissent Triggers

| ID | Condition | Recommendation | Confidence |
|----|-----------|---------------|------------|
| DT-TRUNK-008 | Route list has 3+ route group members | Flag for manual review — static "use first route group" heuristic may select the wrong primary. Operator should verify which route group handles the majority of traffic before accepting. | 0.80 |
| DT-TRUNK-009 | Route list referenced by 5+ dial plans | Route list is a critical shared resource. Splitting it affects all referencing dial plans. Recommend operator maps the full dial plan → route list → route group topology before deciding. | 0.85 |

## See Also

- `docs/reference/call-routing.md` -- Full Webex call routing API reference (trunks, route groups, dial plans, translation patterns, PSTN config)
- `docs/reference/emergency-services.md` -- E911 implications for PSTN routing
- `src/wxcli/migration/advisory/advisory_patterns.py` -- Pattern 8 (trunk consolidation), Pattern 12 (CPN transformation), Pattern 13 (PSTN connection type), Pattern 19 (transformation patterns), Pattern 32 (route list complexity)
- `docs/knowledge-base/migration/kb-css-routing.md` -- CSS/partition routing decisions (related: dial plan scoping differences)

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | Route groups max 10 trunks | Yes | `call-routing.md` lines 58, 820 | "A Route Group bundles up to 10 trunks" confirmed twice. |
| 2 | Trunk types (Local Gateway, CCPSTN, Premises) | Yes | `call-routing.md` PSTNType enum lines 1571-1575 | `LOCAL_GATEWAY`, `NON_INTEGRATED_CCP`, `INTEGRATED_CCP`, `CISCO_PSTN` confirmed. Doc adds Cisco Calling Plan as 4th type beyond plan's 3. |
| 3 | No H.323 support | Not in docs | `call-routing.md` TrunkType enum | TrunkType only has REGISTERING and CERTIFICATE_BASED (both SIP). No H.323 type exists. Absence strongly implies SIP-only but no explicit "H.323 not supported" statement found. Marked `<!-- From training, needs verification -->`. |
