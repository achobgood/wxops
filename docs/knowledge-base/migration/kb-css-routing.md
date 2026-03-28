# CSS & Routing: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

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
<!-- Source: advisory_patterns.py line 117, location-call-settings-core.md Internal Dialing section -->

### Multi-site CUCM with per-site CSS/partition sets

Multi-site CUCM deployments typically have one CSS per site (e.g., `NYC-CSS`, `LAX-CSS`), each containing site-specific partitions plus shared partitions. The `location_consolidation` pattern (advisory_patterns.py line 225) detects when multiple device pools share the same timezone and region, suggesting they map to a single Webex location. The routing implications: each site's CSS patterns become part of org-wide Webex dial plans. Per-site routing isolation is lost -- all patterns are visible to all users. Site-specific routing must be achieved via translation patterns (location-level) or trunk/route group assignment.
<!-- From training, needs verification -->

### Time-of-day routing via partition time schedules

The `detect_partition_time_routing` pattern (advisory_patterns.py line 615) fires when partitions have `timeScheduleIdName` or `time_schedule_name` set. In CUCM, time-of-day routing works by making partitions active only during specific time windows. The CSS then routes differently at different times because different partitions are reachable. Webex has no partition time schedule concept. The equivalent is Auto Attendant business hours / after-hours menus, which route calls to different destinations based on a schedule attached to the AA.
<!-- Source: advisory_patterns.py lines 644-650 -->

---

## Webex Constraints

**Dial plans are org-wide, not per-location.** Dial plans are configured globally for an enterprise and apply to all users regardless of location. Each dial plan contains one or more dial patterns and is associated with a single routing choice (trunk or route group).
<!-- Verified: call-routing.md line 55: "Dial Plans are configured globally (org-wide, not per-location)" and line 128: "configured globally for an enterprise and apply to all users, regardless of location" -->

**Translation patterns can be org-level or location-level.** The `TranslationPatternsApi.create()` method accepts an optional `location_id` parameter -- omit it for org-level, set it for location-level. Org-level patterns live at `/telephony/config/callRouting/translationPatterns`, location-level at `/telephony/config/locations/{locationId}/callRouting/translationPatterns`.
<!-- Verified: call-routing.md line 60 and lines 1363-1364, 1489, 1529 -->

**No partition ordering -- longest-match only.** Webex matches dialed digits against all dial plan patterns across the org and selects the longest (most specific) match. There is no concept of partition position or priority among patterns.
<!-- Verified: call-routing.md Architecture Overview lines 55-56 -->

**Calling permissions are per-person, per-workspace, and per-location.** The `OutgoingPermissionsApi` is used for person, workspace, location, and virtual line settings. Each entity can have custom outgoing permissions that control which call types (INTERNAL, NATIONAL, INTERNATIONAL, PREMIUM_SERVICES_I, etc.) are allowed, blocked, or require auth codes.
<!-- Verified: person-call-settings-permissions.md line 136: "Also used for: user, workspace, location, virtual line settings" and lines 143-161 for call type enum. Access codes endpoint exists at location level: `/telephony/config/locations/{locationId}/outgoingPermission/accessCodes` per location-call-settings-media.md line 594 -->

**Route groups max 10 trunks.** A route group bundles up to 10 trunks from different locations with priority-based failover.
<!-- Verified: call-routing.md line 58: "bundles up to 10 trunks" and line 820: "collection of trunks (up to 10, from different locations)" -->

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

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | Dial plans are org-wide | Yes | `call-routing.md` line 55, line 128 | "Dial Plans are configured globally (org-wide, not per-location)" confirmed twice. |
| 2 | Route groups max 10 trunks | Yes | `call-routing.md` line 58, line 820 | "A Route Group bundles up to 10 trunks (from different locations)" confirmed twice. |
| 3 | Calling permissions are per-location | Expanded | `person-call-settings-permissions.md` line 136; `location-call-settings-media.md` line 594 | Calling permissions exist at person, workspace, location, AND virtual line levels — not just per-location. Doc updated to reflect full scope. |
