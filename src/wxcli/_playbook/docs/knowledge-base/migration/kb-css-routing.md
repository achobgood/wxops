# CSS & Routing: Migration Knowledge Base

> **Audience:** Migration advisor agent (Opus) and cold-context Claude sessions looking up dissent triggers, decision context, and Webex constraints for CSS / dial plan / routing decisions.
> **Reading mode:** Reference. Grep by `DT-CSS-NNN` ID for dissent triggers, OR read `## Decision Framework` end-to-end when the migration-advisor agent loads this doc during analysis.
> **See also:** [Operator Runbook](../../runbooks/cucm-migration/operator-runbook.md) · [Decision Guide](../../runbooks/cucm-migration/decision-guide.md) · [Tuning Reference](../../runbooks/cucm-migration/tuning-reference.md)

## Decision Framework

### CSS_ROUTING_MISMATCH

The `recommend_css_routing_mismatch()` rule in `recommendation_rules.py` dispatches on `mismatch_type` from the decision context. Three cases:

**`partition_ordering`** -- Recommends `manual`. The CSS depends on partition ordering to resolve a specific pattern. Webex uses longest-match routing with no partition ordering equivalent. The rule returns: "Review manually." Reasoning: partition ordering in CUCM means the first partition in the CSS that contains a matching pattern wins, regardless of pattern specificity. In Webex, the most specific (longest) pattern always wins. These are fundamentally different algorithms, so automated mapping is unsafe.

**`scope_difference`** -- Recommends `use_union`. The rule returns: "Union preserves all routing for all users at this location." Reasoning: when CSSes differ only in which partitions are included (not in overlapping patterns), taking the union of all partitions' patterns into a single Webex dial plan preserves reachability for all users. No patterns conflict, so union is safe. This works because Webex dial plans are org-wide -- every user can reach every pattern in every dial plan. The scope difference that CUCM achieves via CSS assignment disappears in Webex's flat namespace.

**`pattern_conflict`** -- Recommends `manual`. The rule identifies that the same pattern routes to different destinations depending on which dial plan (CSS) it appears in. Returns: "Pattern '{pattern}' routes to {route_a} in {dp_a} and {route_b} in {dp_b}. The correct route depends on business intent." This requires human judgment because Webex cannot have the same pattern route to two different destinations.

### CALLING_PERMISSION_MISMATCH

The `recommend_calling_permission_mismatch()` rule maps CUCM blocking patterns to Webex outgoing call type policies. Two prefix families:

**International prefixes** (`011`, `00`, `+2` through `+9`) -- Maps to `INTERNATIONAL_CALL`. CUCM restriction CSSes that block patterns starting with these prefixes are implementing international call blocking. Webex has a native `INTERNATIONAL` call type in outgoing permissions that can be set to `BLOCK`.
<!-- Source: recommendation_rules.py lines 352-353, person-call-settings-permissions.md §2 OutgoingPermissionCallType enum -->

**Premium/toll prefixes** (`1900`, `900`, `976`) -- Maps to `PREMIUM_SERVICES_NUMBER_ONE`. These CUCM blocking patterns target premium-rate numbers. Webex has `PREMIUM_SERVICES_I` and `PREMIUM_SERVICES_II` call types.
<!-- Source: recommendation_rules.py lines 354, person-call-settings-permissions.md §2 OutgoingPermissionCallType enum -->

The mapping is straightforward because CUCM restriction CSSes encode call type policies as explicit digit pattern blocks, while Webex provides named call type categories that cover the same number ranges at a higher abstraction level. Patterns that don't match either prefix family return `None` (no recommendation) to force manual review.

### CSS Decomposition: Union vs Intersection vs Manual

CUCM CSSes can represent two fundamentally different policies:

**Additive (union) CSSes** -- The CSS grants access to partitions the user needs to reach. Each partition adds reachable destinations. Example: a user's CSS includes `Internal-PT`, `Local-PT`, `LD-PT`. These are additive -- the user can reach internal extensions, local numbers, and long-distance numbers. Migration: take the union of all patterns across partitions into Webex dial plans. This is the `scope_difference` case above.

**Restrictive (intersection) CSSes** -- The CSS limits what a user can dial by omitting partitions. Example: `Restricted-CSS` includes `Internal-PT` and `Local-PT` but excludes `International-PT`. The absence of the international partition is the policy. Migration: the restriction maps to Webex outgoing calling permissions (block `INTERNATIONAL`), not to dial plans. This is the `restriction_css_consolidation` advisory pattern case.

**How to distinguish them:**
- If ALL partitions in the CSS contain only patterns with `blockEnable=True`, it's a restriction CSS. The `detect_restriction_css_consolidation` pattern uses exactly this check.
<!-- Source: advisory_patterns.py lines 53-76 -->
- If the CSS contains a mix of routing patterns and blocking patterns, it's a hybrid that requires manual decomposition -- separate the routing patterns into dial plans and the blocking intent into calling permissions.
- If the CSS differs from another CSS only by which partitions are included (no overlapping patterns with different destinations), it's additive and safe for union.

---

## Edge Cases & Exceptions

### CSSes mixing routing and restriction partitions

A single CSS may contain both routing partitions (patterns that route to trunks/gateways) and restriction partitions (patterns with `blockEnable=True`). The `restriction_css_consolidation` pattern only fires when ALL partitions contain ONLY blocking patterns. A mixed CSS will not trigger the advisory, which means its restriction intent may be missed during migration. The operator must manually identify the blocking partitions and map them to calling permissions while mapping the routing partitions to dial plans.

### Partition ordering with overlapping patterns (CRITICAL)

The `detect_partition_ordering_loss` pattern (advisory_patterns.py line 667) is the highest-severity advisory in the system (`CRITICAL`). It fires when:
1. A CSS has partitions containing overlapping patterns (checked via `cucm_patterns_overlap()`)
2. Those patterns appear at different partition ordinals
3. The overlapping patterns route to different destinations
<!-- Source: advisory_patterns.py lines 738-743: `if dest_a != dest_b and ord_a != ord_b` -->

In CUCM, the lower-ordinal partition wins. In Webex, the longest (most specific) match wins. If a shorter pattern in partition 1 would win in CUCM but a longer overlapping pattern in partition 3 would win in Webex, calls route differently after migration. The affected objects list includes the CSS, all involved partitions, and all route patterns from those partitions.

### Translation patterns doing more than digit normalization

The `detect_translation_pattern_elimination` pattern (advisory_patterns.py line 120) uses three heuristics to identify digit normalization:
1. Prefix strip: pattern matches `^\d+\.` regex (e.g., `9.XXXX` strips the leading 9)
2. E.164 insertion: replacement starts with `+` or `\+`
3. Access code removal: matching pattern has `.` but replacement does not

Patterns that don't match these heuristics are NOT flagged for elimination. This means translation patterns implementing inter-site short-code routing (e.g., `8XXX` -> `+1919555XXXX` for a specific site) would be flagged if the replacement starts with `+`, even though this is business logic, not normalization. See DT-CSS-003 below.

### Restriction CSSes that should become dial plans

When a restriction CSS contains patterns that block specific digit strings but the business intent is to route those calls differently (not block them), the correct Webex mapping is a dial plan pointing to an alternate trunk, not a calling permission block. The `restriction_css_consolidation` pattern cannot detect this distinction -- it only checks `blockEnable`. Operator review is required when restriction CSSes serve dual routing/blocking purposes.

---

## Real-World Patterns

### Globalized vs localized dial plans

The `detect_globalized_vs_localized` pattern (advisory_patterns.py line 995) classifies the deployment's dial plan style by counting E.164 patterns (those starting with `+`):
- **>50% E.164** = globalized. Maps well to Webex, which uses E.164 natively. Translation patterns doing E.164 conversion are likely redundant.
- **<20% E.164** = localized. Site-specific patterns, local digit dialing. Configure each Webex location's `outside_dial_digit` and internal dialing prefix to match local behavior.
- **20-50% E.164** = hybrid. Partial migration to E.164 or inconsistent multi-site standards. Requires manual standardization.
<!-- Source: advisory_patterns.py lines 1019-1056 -->

### The "9 for outside line" pattern

CUCM deployments commonly use a `9.` prefix for outside line access. This appears as translation patterns that strip the leading 9 (matching `9.XXXX`, replacing with `XXXX`). The `translation_pattern_elimination` pattern catches these via the `_PREFIX_STRIP_RE` regex (`^\d+\.`). In Webex, configure the location's `outside_dial_digit` setting to `9` and Webex handles the stripping natively -- no translation pattern needed.
<!-- Source: advisory_patterns.py line 117, location-calling-core.md Internal Dialing section -->

### Multi-site CUCM with per-site CSS/partition sets

Multi-site CUCM deployments typically have one CSS per site (e.g., `NYC-CSS`, `LAX-CSS`), each containing site-specific partitions plus shared partitions. The `location_consolidation` pattern (advisory_patterns.py line 225) detects when multiple device pools share the same timezone and region, suggesting they map to a single Webex location. The routing implications: each site's CSS patterns become part of org-wide Webex dial plans. Per-site routing isolation is lost -- all patterns are visible to all users. Site-specific routing must be achieved via translation patterns (location-level) or trunk/route group assignment.

### Time-of-day routing via partition time schedules

The `detect_partition_time_routing` pattern (advisory_patterns.py line 615) fires when partitions have `timeScheduleIdName` or `time_schedule_name` set. In CUCM, time-of-day routing works by making partitions active only during specific time windows. The CSS then routes differently at different times because different partitions are reachable. Webex has no partition time schedule concept. The equivalent is Auto Attendant business hours / after-hours menus, which route calls to different destinations based on a schedule attached to the AA.
<!-- Source: advisory_patterns.py lines 644-650 -->

---

## Webex Constraints

**Dial plans are org-wide, not per-location.** Dial plans are configured globally for an enterprise and apply to all users regardless of location. Each dial plan contains one or more dial patterns and is associated with a single routing choice (trunk or route group).

**Translation patterns can be org-level or location-level.** The `TranslationPatternsApi.create()` method accepts an optional `location_id` parameter -- omit it for org-level, set it for location-level. Org-level patterns live at `/telephony/config/callRouting/translationPatterns`, location-level at `/telephony/config/locations/{locationId}/callRouting/translationPatterns`.

**No partition ordering -- longest-match only.** Webex matches dialed digits against all dial plan patterns across the org and selects the longest (most specific) match. There is no concept of partition position or priority among patterns.

**Calling permissions are per-person, per-workspace, and per-location.** The `OutgoingPermissionsApi` is used for person, workspace, location, and virtual line settings. Each entity can have custom outgoing permissions that control which call types (INTERNAL, NATIONAL, INTERNATIONAL, PREMIUM_SERVICES_I, etc.) are allowed, blocked, or require auth codes.

**Route groups max 10 trunks.** A route group bundles up to 10 trunks from different locations with priority-based failover.

---

## Dissent Triggers

### DT-CSS-001: Partition ordering loss flagged but all overlapping patterns route to same destination

**Condition:** `partition_ordering_loss` advisory fires AND all overlapping patterns at different partition positions have destinations that resolve to the same trunk or route group.

**Why static fires incorrectly:** The `detect_partition_ordering_loss` pattern checks `if dest_a != dest_b and ord_a != ord_b` (advisory_patterns.py line 742). However, destination comparison uses the raw `destination` or `routeDestination` field from `pre_migration_state`. If two trunks in different partitions ultimately route to the same SBC but are represented as different CUCM trunk objects, the string comparison will see different values even though the actual call destination is identical. Additionally, if all overlapping patterns DO have matching destinations (same string), the pattern correctly does NOT fire. This dissent trigger covers the case where destinations are semantically identical but syntactically different.

**Advisor should:** Check whether the reported overlapping destinations resolve to the same physical endpoint (same SBC/gateway IP). If yes, recommend accepting the advisory with a note that partition ordering is irrelevant for this specific case since all paths lead to the same destination. If destinations are truly different, the advisory is correct and manual resolution is required.

**Confidence:** HIGH -- the overlap detection is sound, but destination comparison is string-based and cannot resolve trunk-to-gateway mappings.

### DT-CSS-002: Restriction CSS recommended for elimination but contains non-blocking patterns

**Condition:** `restriction_css_consolidation` fires AND the CSS contains partitions where the pattern check missed a mixed-use partition. Specifically: a partition has patterns where `blockEnable` is not set in `pre_migration_state` (field missing or `None`) but the partition's route patterns are configured to route to a "blocked" destination (e.g., an announcement saying "this call is not allowed").

**Why static fires incorrectly:** The pattern checks `pre.get("blockEnable", False)` (advisory_patterns.py line 71). If `blockEnable` is `False` or missing, the pattern is treated as non-blocking and the CSS is excluded. But CUCM has multiple ways to implement call blocking: `blockEnable=True` is the explicit flag, but routing to an announcement or CTI route point that plays a recording and disconnects achieves the same result without setting `blockEnable`. The heuristic only detects the explicit flag.

**Advisor should:** When the advisory fires, verify that the identified CSSes truly contain ONLY restriction patterns by checking the destinations of all patterns, not just the `blockEnable` flag. If any pattern routes to a legitimate destination (trunk, gateway, voicemail pilot) rather than a blocking announcement, flag the CSS for manual decomposition -- it serves dual routing and restriction purposes.

**Confidence:** MEDIUM -- the `blockEnable` check is reliable when the field is populated, but CUCM configurations that use implicit blocking (route to announcement) will be missed.

### DT-CSS-003: Translation pattern flagged for elimination but implements inter-site routing

**Condition:** `translation_pattern_elimination` fires AND the pattern transforms a short code to a full E.164 with a site-specific prefix (e.g., `8XXX` -> `+14155551XXX` for the SF office).

**Why static fires incorrectly:** The heuristic at advisory_patterns.py line 144 matches any pattern where the replacement starts with `+` or `\+`. This correctly identifies E.164 normalization (stripping a dial prefix and adding country code) but also matches inter-site short-code translation, which is business logic. Short codes like `8XXX` for "call the SF office" are not simple digit normalization -- they encode organizational routing decisions that must be preserved.

**Advisor should:** When the advisory fires and affected patterns include short-code-to-E.164 translations (matching pattern is a short digit string like 1-4 digits, not a full number with prefix strip), recommend keeping the translation pattern. Webex supports location-level translation patterns that can implement the same short-code routing. The pattern should be recreated as a Webex translation pattern at the appropriate location, not eliminated.

**Confidence:** MEDIUM -- the `+` prefix heuristic has a known false positive rate for short-code patterns. The detection could be improved by checking whether the matching pattern length is significantly shorter than the replacement (indicating business-logic transformation rather than normalization), but the current code does not make this distinction.

### DT-CSS-004: Restriction CSS flagged for elimination but contains pattern-specific allow exceptions

**Condition:** `restriction_css_consolidation` advisory fires AND one or more partitions in the CSS contain route patterns where `blockEnable` is `True` alongside a route pattern in a different partition within the same CSS that does NOT have `blockEnable=True` — i.e., the CSS is not purely restriction-only but the static check still qualifies it because it short-circuits on the first non-blocking partition.

**Why static fires incorrectly:** `detect_restriction_css_consolidation` (advisory_patterns.py:41) walks `css_contains_partition` cross-refs and checks each pattern's `pre_migration_state.blockEnable`. It breaks out of the inner loop at the first non-blocking pattern it finds (`all_blocking = False; break`). If a CSS has one partition with all-blocking patterns followed by a second partition with one non-blocking "allow exception" route pattern (e.g., `blockEnable=False` with a route to a specific international carrier for approved executive calls), the CSS correctly fails the `all_blocking` test and is excluded. However, the more common problem is the **inverse case**: a CSS where one partition is legitimately routing (non-blocking) but another partition implements a narrowly scoped exception route pattern that the operator intends as a policy override — for example, a single route pattern `011 972 XXXXXXX` that routes international calls to Israel to a specific trunk (approved by compliance). This is not "just a restriction CSS" and it is not "just a routing CSS." The Webex calling permission system (`OutgoingPermissions`, `person-call-settings-permissions.md:130-187`) works at the call-type level (INTERNATIONAL_CALL, NATIONAL, etc.) with no per-destination pattern override; there is no mechanism to say "block all international except +972." Migrating this as calling permissions silently drops the exception.

**Advisor should:** When `restriction_css_consolidation` fires, inspect the `affected_objects` list and for each CSS, check whether any partition contains patterns that route to a legitimate destination (trunk, gateway) rather than a blocking destination. If yes — particularly if any matching pattern is a narrow E.164 prefix like `011 NXX` or `\+NNNN` routing to a specific trunk — flag the CSS for manual decomposition. The restriction component can become a calling permission; the allow-exception component must become an explicit dial plan entry with a narrow pattern, or an `AUTH_CODE` permission, depending on the business intent. Cite `recommend_calling_permission_mismatch` (recommendation_rules.py:406) which maps international block patterns to `INTERNATIONAL_CALL` permission but has no logic for per-destination overrides.

**Confidence:** MEDIUM -- the static check reliably identifies pure restriction CSSes. The false-positive rate is low, but large enterprises with compliance-driven per-destination exceptions are exactly the customers most likely to encounter this.

### DT-CSS-005: Extension-range dial plan flagged as redundant but routes to non-default destination

**Condition:** `overengineered_dial_plan` advisory fires AND any of the flagged dial plans route their `XXXX` / `[2-9]XXX` patterns to a destination that is NOT the default intra-location extension path — specifically, a hunt list, CTI route point, or non-standard trunk.

**Why static fires incorrectly:** `detect_overengineered_dial_plan` (advisory_patterns.py:384) uses `_EXT_RANGE_RE = r"^(\[[\d-]+\])?X{2,4}$"` plus a literal `XXXX` check against `dp.get("dial_patterns", [])`. It fires when 2+ dial plans contain extension-range patterns. The rule assumes that any `XXXX`-style pattern in a dial plan is redundant because "Webex automatically routes calls to extensions within the location's configured range" (advisory_patterns.py:411). This is correct for patterns that were added merely to bootstrap intra-site calling in CUCM. However, CUCM operators also use `XXXX` and `[2-9]XXX` as catch-all route patterns pointing at specific destinations — for example, a `XXXX` pattern pointing at a hunt pilot (so all unresolved 4-digit dials hit a secretary group), or a `[2-9]XXX` pointing at a CTI route point for IVR integration. Webex's built-in extension routing sends unresolved 4-digit dials to a "number not found" treatment, not to a catch-all hunt group. Eliminating these patterns silently changes call behavior.

**Advisor should:** Before recommending elimination, verify the dial plan's routing destination. If the destination is a hunt pilot, call queue, CTI route point, or any non-trunk destination, flag the pattern for manual review. The pattern is not redundant — it implements a deliberate call flow that must be rebuilt in Webex as either a location-level dial plan entry or an auto attendant extension rule. Cite the `overengineered_dial_plan` pattern name in the dissent so the operator can find the relevant dial plan objects in the `affected_objects` list. Reference `call-routing.md:55-61` (dial plans are org-wide pattern match → routing choice) — Webex has no "catch-all by extension range" routing concept analogous to a CUCM hunt pilot catch-all.

**Confidence:** HIGH -- the `_EXT_RANGE_RE` regex correctly identifies extension-range patterns, but the static rule performs no check on where those patterns actually route. Any migration with hunt pilots or CTI route points receiving catch-all extension traffic will encounter this.

### DT-CSS-006: Translation pattern flagged for elimination but dial plan mixes globalized and localized addressing

**Condition:** `translation_pattern_elimination` fires AND `globalized_vs_localized` classifies the dial plan style as `hybrid` (20%-50% E.164 patterns) — indicating the CUCM deployment uses both `+E.164` and localized (access-code prefixed, site-digit) addressing simultaneously.

**Why static fires incorrectly:** `detect_translation_pattern_elimination` (advisory_patterns.py:120) identifies translation patterns that strip access-code prefixes or insert country codes, and recommends migrating them as Webex location `outside_dial_digit` settings. This recommendation is sound for a uniformly localized dial plan, but in a hybrid deployment, some sites are already using `+E.164` directly while others use the traditional `9.XXXX` local dial pattern. The two halves of the dial plan are stitched together by translation patterns that bridge them. Eliminating the translation patterns and setting `outside_dial_digit=9` for the localized half would break the E.164 sites — their calls would have the digit-9 strip applied when it was never dialed. Webex's `outside_dial_digit` is a per-location setting (confirmed in `call-routing.md:60-61` and `detect_globalized_vs_localized` at advisory_patterns.py:995-1056), but locations do not have awareness of whether a given user dialed via a legacy 9-prefix convention or a clean E.164 path. There is no per-pattern `outside_dial_digit` override.

**Advisor should:** When both `translation_pattern_elimination` and a hybrid `globalized_vs_localized` finding are present in the same migration, flag the translation patterns for manual review instead of recommending elimination. The correct migration path for hybrid environments is to standardize on E.164 as the primary dial plan style in Webex, preserve the translation patterns as Webex location-level translation patterns (not eliminated), and configure `outside_dial_digit` only for locations confirmed to use legacy access-code dialing. Reference `call-routing.md:60` ("Translation Patterns manipulate dialed digits before routing — they can be applied at the organization level or location level") and the `globalized_vs_localized` hybrid detail text ("mixes globalized and localized dial plan styles ... usually indicates a partial migration to E.164 or multi-site with inconsistent standards and needs manual review").

**Confidence:** MEDIUM -- the advisory fires reliably, but the hybrid classification threshold (20-50% E.164) makes this condition common enough to warrant a standing dissent trigger. Hybrid environments are the norm in multi-site enterprises mid-way through an E.164 conversion.

### DT-CSS-007: Partition-ordering-loss flagged but overlapping patterns have different caller-ID transforms per partition

**Condition:** `partition_ordering_loss` advisory fires AND at least one overlapping pattern pair has the same trunk destination (same `destination` / `routeDestination` string in `pre_migration_state`) but different `callingPartyTransformationMask` values per partition, indicating that the partition ordering controls outbound caller ID rather than routing destination.

**Why static fires incorrectly:** `detect_partition_ordering_loss` (advisory_patterns.py:667) compares destinations at line 742 via `dest_a != dest_b` where `dest` is populated as `pre.get("destination", "") or pre.get("routeDestination", "") or rp_id`. The static check fires only when destinations differ — but a compliance-routing pattern in CUCM often uses partition ordering to apply a different `callingPartyTransformationMask` per route (e.g., `PT_SiteA_PSTN` ordinal 1: `9.XXXXXXXXXX` → trunk with mask `4085551XXX`; `PT_SiteB_PSTN` ordinal 2: same pattern → same trunk with mask `4085552XXX`). Both partitions route to the same trunk object. The `dest` field resolves identically for both, so `dest_a == dest_b` and the pattern does NOT fire at all — the ordering loss is invisible to the static check. The human operator sees no CRITICAL advisory and may not realize that after migration, all callers from both sites share a single flat caller ID set at the user/location level in Webex (`recommend_css_routing_mismatch` at recommendation_rules.py:370 handles the `mismatch_type == "partition_ordering"` case but only fires when the `CSS_ROUTING_MISMATCH` analyzer produces a decision, which requires the routing destinations to differ). The loss is silent.

**Advisor should:** When `partition_ordering_loss` fires, also scan the affected partitions' route patterns for `callingPartyTransformationMask` fields that differ across overlapping patterns. If any such difference exists, flag it as a CPN compliance risk distinct from routing destination loss. The correct Webex migration path is to consolidate caller ID to the user or location level (`person-call-settings-permissions.md:130` outgoing permissions, caller ID settings per user). If different caller IDs are legally required per call path (DNIS-based caller ID for compliance routing), document the limitation — Webex does not support per-dial-plan-entry caller ID masking. Cite `detect_cpn_transformation_chain` (advisory_patterns.py line 801) which tracks CPN transformations on route patterns and trunks but does not cross-reference partition ordering context.

**Confidence:** HIGH -- this gap follows directly from the `dest_a != dest_b` guard at advisory_patterns.py:742. Any migration with compliance-driven per-site outbound caller ID routing through ordered partitions will encounter it, and no existing pattern fires to surface it.

### DT-CSS-008: Partition-ordering-loss flagged for overlapping patterns whose ordering implements time-of-day routing via CSS, not partition schedule

**Condition:** `partition_ordering_loss` fires AND `detect_partition_time_routing` does NOT fire AND the overlapping partition pair includes one partition that is only populated during business hours and one during after-hours — i.e., the time-of-day dimension is encoded in which partition is active in the CSS at a given time, not in a `timeScheduleIdName` on the partition object itself.

**Why static fires incorrectly:** `detect_partition_time_routing` (advisory_patterns.py:615) only checks `pre_migration_state.timeScheduleIdName` or `time_schedule_name` on the partition object. CUCM supports a second time-of-day pattern: the CSS itself includes both a day-partition and a night-partition, and a CUCM time period object activates or deactivates the CSS membership at runtime rather than setting a schedule on the partition. In this architecture, neither partition has a `timeScheduleIdName` field — the temporal logic lives at the CSS-context level (or in CUCM's `Time Period` / `Time Schedule` objects linked to the CSS, not the partition). `detect_partition_time_routing` sees no schedule and does not fire. `detect_partition_ordering_loss` fires because the two partitions contain overlapping patterns with different destinations (business-hours AA vs. after-hours AA), but its CRITICAL recommendation is to "resolve the overlap by making one pattern more specific or removing the redundant pattern" — which is wrong. The two patterns are intentionally identical; the operator needs to configure Webex Auto Attendant business-hours schedules, not simplify the dial plan.

**Advisor should:** When `partition_ordering_loss` fires and the overlap involves a pattern pair whose destinations resolve to auto attendant or announcement objects (not trunks), consider whether the overlap encodes time-of-day intent. If the destination of one partition is a business-hours AA and the destination of the other is an after-hours AA, recommend migrating to Webex Auto Attendant business-hours/after-hours schedule configuration rather than resolving the overlap as a routing conflict. Reference `detect_partition_time_routing` (advisory_patterns.py:615) — explain to the operator that the standard time-routing pattern did not fire because the schedule is attached at the CSS level rather than the partition level, but the functional intent is the same. The correct Webex path is the same: Auto Attendant schedules, not dial plan simplification.

**Confidence:** MEDIUM -- the time-of-day-via-CSS pattern is less common than the time-of-day-via-partition pattern and the signals from `pre_migration_state` fields alone may not reliably distinguish the two. An operator who sees a CRITICAL partition-ordering-loss advisory for patterns pointing at AA objects should always check for this before resolving.

---

## Selective Call Handling Detection

Three heuristics in `SelectiveCallHandlingAnalyzer` detect CUCM CSS/partition
patterns that imply per-caller routing differences:

1. **Multi-partition DN** — same DN appears in 2+ partitions reachable via
   different user CSSes. Indicates the operator modelled "internal callers
   reach me directly; external callers hit forwarding rules" by placing the
   DN in two partitions with different CSS scopes.
2. **Low-membership partition** — partition with ≤10 DNs that appears in
   fewer than half of all CSSes. Indicates a VIP/executive bypass pattern
   where only certain CSSes can reach this partition.
3. **Naming convention** — partition name matches `vip`, `executive`,
   `priority`, `direct`, `bypass`, `afterhours`, or `emergency`. Weak
   signal — only LOW severity unless paired with a structural signal.

Each heuristic produces a `FEATURE_APPROXIMATION` decision tagged with
`selective_call_handling_pattern` in the context. The recommendation rule
always suggests `accept` (configure Webex selective forwarding/acceptance/
rejection or Priority Alert post-migration). The pipeline does NOT
auto-create selective rules — phone-number criteria require operator review.

The advisory pattern `detect_selective_call_handling_opportunities` aggregates
all selective decisions into a single cross-cutting `ARCHITECTURE_ADVISORY`.

**Mitigation 1: multi-site false positives.** Multi-partition DNs are
filtered out when the owning users live at different `location_id` values
(this is a multi-site routing pattern, not selective call handling).

**Mitigation 2: weak naming signal.** Naming-only matches stay LOW severity.
A structural confirmation (multi-partition DN OR low-membership subset) is
required for MEDIUM severity.

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | Dial plans are org-wide | Yes | `call-routing.md` line 55, line 128 | "Dial Plans are configured globally (org-wide, not per-location)" confirmed twice. |
| 2 | Route groups max 10 trunks | Yes | `call-routing.md` line 58, line 820 | "A Route Group bundles up to 10 trunks (from different locations)" confirmed twice. |
| 3 | Calling permissions are per-location | Expanded | `person-call-settings-permissions.md` line 136; `location-calling-media.md` line 594 | Calling permissions exist at person, workspace, location, AND virtual line levels — not just per-location. Doc updated to reflect full scope. |
