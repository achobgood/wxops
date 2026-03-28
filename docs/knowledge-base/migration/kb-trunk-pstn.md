# Trunk & PSTN: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

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

## Webex Trunk Types

Two trunk types exist in Webex Calling, determined at creation time and immutable after:
<!-- Source: call-routing.md §Trunks, TrunkType enum -->

| Type | API Value | Use Case | Authentication | Required Fields |
|------|-----------|----------|---------------|-----------------|
| **Registering** | `REGISTERING` | Cisco CUBE Local Gateway. SBC registers with Webex cloud. | Password-based (SIP registration) | `name`, `locationId`, `password` |
| **Certificate-based** | `CERTIFICATE_BASED` | Third-party SBCs: AudioCodes, Ribbon, Oracle ACME, Cisco UBE. Uses mutual TLS. | mTLS certificate | `name`, `locationId`, `password`, `address` (FQDN/SRV), `domain`, `port`, `maxConcurrentCalls` |

**Immutable after creation:** `trunkType`, `locationId`, `deviceType`. Must delete and recreate to change these.
<!-- Source: call-routing.md §Update Trunk limitation -->

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

## See Also

- `docs/reference/call-routing.md` -- Full Webex call routing API reference (trunks, route groups, dial plans, translation patterns, PSTN config)
- `docs/reference/emergency-services.md` -- E911 implications for PSTN routing
- `src/wxcli/migration/advisory/advisory_patterns.py` -- Pattern 8 (trunk consolidation), Pattern 12 (CPN transformation), Pattern 13 (PSTN connection type), Pattern 19 (transformation patterns)
- `docs/knowledge-base/migration/kb-css-routing.md` -- CSS/partition routing decisions (related: dial plan scoping differences)
