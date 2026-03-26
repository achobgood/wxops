"""CSS decomposition mapper: CUCM CSS -> Webex Dial Plans + Calling Permissions.

Decomposes CUCM Calling Search Spaces into:
- Webex Calling Dial Plans (org-wide routing)
- Per-user Outgoing Calling Permissions (category-based blocking)

Implements the 5-step algorithm from 04-css-decomposition.md.

(from 03b-transform-mappers.md §7, css_mapper)
(from 04-css-decomposition.md, full algorithm)

Cross-ref reads:
    css_contains_partition      (#16) — ordered partitions in a CSS
    partition_has_pattern        (#17) — route patterns in a partition
    user_has_css                 (#18) — user -> CSS assignment
    device_has_css               (#19) — device -> CSS assignment
    line_has_css                 (#20) — line -> CSS assignment

Decisions generated:
    CSS_ROUTING_MISMATCH         — routing scope differences, MIXED partitions, ordering conflicts
    CALLING_PERMISSION_MISMATCH  — unclassifiable block patterns
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.models import (
    CallingPermissionEntry,
    CanonicalCallingPermission,
    CanonicalDialPlan,
    DecisionType,
    MapperResult,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cucm_pattern import (
    classify_block_pattern,
    cucm_patterns_overlap,
)
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    decision_to_store_dict,
    hash_id,
    manual_option,
    skip_option,
)
from wxcli.migration.transform.pattern_converter import cucm_to_webex_pattern

logger = logging.getLogger(__name__)

# Webex OutgoingPermissionCallType values
# (from docs/reference/person-call-settings-permissions.md)
WEBEX_CALL_TYPES = [
    "INTERNAL_CALL",
    "TOLL_FREE",
    "NATIONAL",
    "INTERNATIONAL",
    "OPERATOR_ASSISTED",
    "CHARGEABLE_DIRECTORY_ASSISTED",
    "SPECIAL_SERVICES_I",
    "SPECIAL_SERVICES_II",
    "PREMIUM_SERVICES_I",
    "PREMIUM_SERVICES_II",
]

# Partition classification labels
# (from 04-css-decomposition.md Step 2)
DIRECTORY = "DIRECTORY"
ROUTING = "ROUTING"
BLOCKING = "BLOCKING"
MIXED = "MIXED"


class CSSMapper(Mapper):
    """Decomposes CUCM CSSes into Webex Dial Plans and Calling Permissions.

    Implements the 5-step CSS decomposition algorithm:
    1. Build CSS->Partition->Pattern graph
    2. Classify partitions (DIRECTORY/ROUTING/BLOCKING/MIXED)
    3. Compute routing scope per CSS, intersection baseline
    4. Compute restriction profiles, group users by profile
    5. Detect ordering conflicts via cucm_patterns_overlap()

    (from 03b-transform-mappers.md §7, 04-css-decomposition.md)
    """

    name = "css_mapper"
    depends_on = ["routing_mapper", "user_mapper", "line_mapper", "device_mapper"]

    def __init__(
        self,
        category_rules: list[dict[str, str]] | None = None,
        country_code: str = "+1",
        outside_dial_digit: str = "9",
    ) -> None:
        """Initialize the CSS mapper.

        Args:
            category_rules: Configurable mapping from CUCM block patterns to
                Webex permission categories. Each rule is a dict with
                'cucm_pattern' and 'webex_category' keys.
            country_code: E.164 country prefix for pattern conversion.
            outside_dial_digit: CUCM outside access digit.
        """
        self.category_rules = category_rules or []
        self.country_code = country_code
        self.outside_dial_digit = outside_dial_digit

    def map(self, store: MigrationStore) -> MapperResult:
        """Execute the CSS decomposition algorithm."""
        result = MapperResult()

        # Get all CSS objects
        css_objects = store.get_objects("css")
        if not css_objects:
            logger.info("No CSS objects found — skipping CSS decomposition")
            return result

        # Step 1+2: Build CSS graph and classify partitions
        css_graphs = {}
        for css_data in css_objects:
            css_id = css_data["canonical_id"]
            graph = self._build_css_graph(store, css_id, result)
            if graph:
                css_graphs[css_id] = graph

        if not css_graphs:
            logger.info("No CSS objects with partitions found")
            return result

        # Build combined CSS for users (Line CSS + Device CSS)
        user_effective_css = self._build_user_effective_css(store, css_graphs)

        # Step 3: Compute routing scope per effective CSS, group by scope
        self._compute_routing_scopes(store, css_graphs, user_effective_css, result)

        # Step 4: Compute restriction profiles and create CallingPermissions
        self._compute_restriction_profiles(
            store, css_graphs, user_effective_css, result
        )

        # Step 5: Detect ordering conflicts
        self._detect_ordering_conflicts(store, css_graphs, result)

        return result

    # ------------------------------------------------------------------
    # Step 1+2: Build CSS→Partition→Pattern graph and classify
    # ------------------------------------------------------------------

    def _build_css_graph(
        self,
        store: MigrationStore,
        css_id: str,
        result: MapperResult,
    ) -> dict[str, Any] | None:
        """Build the partition→pattern graph for a CSS, classify partitions.

        Returns a dict with:
            partitions: list of {partition_id, ordinal, classification, patterns}
            patterns is list of {pattern_id, pattern, action}

        (from 04-css-decomposition.md Steps 1-2)
        """
        # Get ordered partitions via css_contains_partition with ordinal
        partition_refs = store.get_cross_refs(
            from_id=css_id, relationship="css_contains_partition"
        )
        if not partition_refs:
            return None

        # Sort by ordinal to preserve CUCM priority order
        partition_refs.sort(key=lambda r: r.get("ordinal") or 0)

        partitions = []
        for ref in partition_refs:
            partition_id = ref["to_id"]
            ordinal = ref.get("ordinal") or 0

            # Get patterns in this partition
            pattern_refs = store.get_cross_refs(
                from_id=partition_id, relationship="partition_has_pattern"
            )

            patterns = []
            for pref in pattern_refs:
                pattern_id = pref["to_id"]
                pat_data = store.get_object(pattern_id)
                if pat_data is None:
                    continue

                state = pat_data.get("pre_migration_state") or {}
                pattern_str = state.get("pattern", "")
                action = state.get("action", "")
                patterns.append({
                    "pattern_id": pattern_id,
                    "pattern": pattern_str,
                    "action": action.upper() if action else "",
                })

            # Classify partition (from 04-css-decomposition.md Step 2)
            classification = self._classify_partition(patterns)

            # Handle MIXED partition — split into virtual ROUTING + BLOCKING
            if classification == MIXED:
                route_patterns = [p for p in patterns if p["action"] == "ROUTE"]
                block_patterns = [p for p in patterns if p["action"] == "BLOCK"]

                # Create virtual ROUTING partition
                partitions.append({
                    "partition_id": f"{partition_id}__virtual_routing",
                    "ordinal": ordinal,
                    "classification": ROUTING,
                    "patterns": route_patterns,
                    "is_virtual": True,
                    "source_partition": partition_id,
                })

                # Create virtual BLOCKING partition
                partitions.append({
                    "partition_id": f"{partition_id}__virtual_blocking",
                    "ordinal": ordinal,
                    "classification": BLOCKING,
                    "patterns": block_patterns,
                    "is_virtual": True,
                    "source_partition": partition_id,
                })

                # Generate CSS_ROUTING_MISMATCH decision for MIXED partition
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.CSS_ROUTING_MISMATCH,
                    severity="MEDIUM",
                    summary=(
                        f"MIXED partition '{partition_id}' in CSS '{css_id}' "
                        f"contains both ROUTE and BLOCK patterns — "
                        f"split into virtual ROUTING + BLOCKING partitions"
                    ),
                    context={
                        "css_id": css_id,
                        "partition_id": partition_id,
                        "reason": "mixed_partition",
                        "route_count": len(route_patterns),
                        "block_count": len(block_patterns),
                    },
                    options=[
                        accept_option(
                            "Accept virtual split into ROUTING + BLOCKING partitions"
                        ),
                        manual_option("Admin manually classifies partition patterns"),
                    ],
                    affected_objects=[css_id, partition_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
            else:
                partitions.append({
                    "partition_id": partition_id,
                    "ordinal": ordinal,
                    "classification": classification,
                    "patterns": patterns,
                    "is_virtual": False,
                })

        return {"partitions": partitions}

    @staticmethod
    def _classify_partition(patterns: list[dict[str, Any]]) -> str:
        """Classify a partition based on its patterns.

        (from 04-css-decomposition.md Step 2)
        """
        if not patterns:
            return DIRECTORY

        has_route = any(p["action"] == "ROUTE" for p in patterns)
        has_block = any(p["action"] == "BLOCK" for p in patterns)

        # Patterns with no action (DNs only) → directory
        has_any_action = has_route or has_block

        if not has_any_action:
            return DIRECTORY
        if has_route and has_block:
            return MIXED
        if has_route:
            return ROUTING
        if has_block:
            return BLOCKING

        return DIRECTORY

    # ------------------------------------------------------------------
    # Combined CSS: Line CSS (higher priority) + Device CSS (lower priority)
    # ------------------------------------------------------------------

    def _build_user_effective_css(
        self,
        store: MigrationStore,
        css_graphs: dict[str, dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Build the effective combined CSS for each user.

        The effective CSS is Line CSS partitions (higher priority) followed by
        Device CSS partitions (lower priority).

        (from 03b-transform-mappers.md §7: CSS on devices vs. users)

        Returns:
            dict mapping user_canonical_id -> combined partition list
        """
        # Gather user→CSS assignments
        user_css_refs = store.get_cross_refs(relationship="user_has_css")
        line_css_refs = store.get_cross_refs(relationship="line_has_css")
        device_css_refs = store.get_cross_refs(relationship="device_has_css")

        # Build index: user_id → css_ids (direct)
        user_css_map: dict[str, list[str]] = defaultdict(list)
        for ref in user_css_refs:
            user_css_map[ref["from_id"]].append(ref["to_id"])

        # Build index: line_id → css_id
        line_css_map: dict[str, str] = {}
        for ref in line_css_refs:
            line_css_map[ref["from_id"]] = ref["to_id"]

        # Build index: device_id → css_id
        device_css_map: dict[str, str] = {}
        for ref in device_css_refs:
            device_css_map[ref["from_id"]] = ref["to_id"]

        # For users with direct CSS assignment, use that directly
        user_effective: dict[str, list[dict[str, Any]]] = {}

        for user_id, css_ids in user_css_map.items():
            combined_partitions = []
            for css_id in css_ids:
                graph = css_graphs.get(css_id)
                if graph:
                    combined_partitions.extend(graph["partitions"])
            if combined_partitions:
                user_effective[user_id] = combined_partitions

        # For users without direct CSS, resolve from line CSS (higher
        # priority) then device CSS (lower priority).  Trace:
        #   user → user_has_device → device → device_has_dn → line
        # Most CUCM deployments assign CSS on the line, not the user.
        users = store.query_by_type("user")
        for user_obj in users:
            uid = user_obj.canonical_id
            if uid in user_effective:
                continue  # already has direct CSS

            combined_partitions: list[dict[str, Any]] = []
            seen_css: set[str] = set()

            # Get user's devices
            device_ids = store.find_cross_refs(uid, "user_has_device")

            for dev_id in device_ids:
                # Line CSS (higher priority) — check DNs on this device
                dn_ids = store.find_cross_refs(dev_id, "device_has_dn")
                for dn_id in dn_ids:
                    css_id = line_css_map.get(dn_id)
                    if css_id and css_id not in seen_css:
                        seen_css.add(css_id)
                        graph = css_graphs.get(css_id)
                        if graph:
                            combined_partitions.extend(graph["partitions"])

                # Device CSS (lower priority)
                css_id = device_css_map.get(dev_id)
                if css_id and css_id not in seen_css:
                    seen_css.add(css_id)
                    graph = css_graphs.get(css_id)
                    if graph:
                        combined_partitions.extend(graph["partitions"])

            if combined_partitions:
                user_effective[uid] = combined_partitions

        return user_effective

    # ------------------------------------------------------------------
    # Step 3: Compute routing scope per CSS
    # ------------------------------------------------------------------

    def _compute_routing_scopes(
        self,
        store: MigrationStore,
        css_graphs: dict[str, dict[str, Any]],
        user_effective_css: dict[str, list[dict[str, Any]]],
        result: MapperResult,
    ) -> None:
        """Compute effective routing scope per CSS, create dial plans.

        Groups CSSes by identical routing scope. If single group, creates
        org-wide dial plans directly. If multiple groups, uses intersection
        as baseline and flags deltas as CSS_ROUTING_MISMATCH decisions.

        (from 04-css-decomposition.md Step 3)
        """
        # Compute routing scope per CSS
        css_routing_scopes: dict[str, frozenset[str]] = {}
        # Track pattern→target mapping for dial plan creation
        pattern_targets: dict[str, tuple[str | None, str | None]] = {}

        for css_id, graph in css_graphs.items():
            route_patterns = set()
            for partition in graph["partitions"]:
                if partition["classification"] == ROUTING:
                    for pat in partition["patterns"]:
                        if pat["action"] == "ROUTE":
                            route_patterns.add(pat["pattern"])
                            # Track the target if available from pre_migration_state
                            pat_data = store.get_object(pat["pattern_id"])
                            if pat_data:
                                state = pat_data.get("pre_migration_state") or {}
                                target_type = state.get("target_type")
                                target_name = state.get("target_name")
                                if target_name and target_type:
                                    if target_type in ("gateway", "trunk"):
                                        pattern_targets[pat["pattern"]] = (
                                            f"trunk:{target_name}",
                                            "TRUNK",
                                        )
                                    elif target_type in (
                                        "route_list",
                                        "routeList",
                                        "route_group",
                                    ):
                                        pattern_targets[pat["pattern"]] = (
                                            f"route_group:{target_name}",
                                            "ROUTE_GROUP",
                                        )
            css_routing_scopes[css_id] = frozenset(route_patterns)

        # Group CSSes by identical routing scope
        scope_groups: dict[frozenset[str], list[str]] = defaultdict(list)
        for css_id, scope in css_routing_scopes.items():
            if scope:  # Skip empty routing scopes
                scope_groups[scope].append(css_id)

        if not scope_groups:
            logger.info("No routing patterns found in any CSS")
            return

        if len(scope_groups) == 1:
            # Happy path: all CSSes have the same routing scope
            # Create org-wide dial plans
            baseline_patterns = next(iter(scope_groups))
            self._create_dial_plans(
                store, baseline_patterns, pattern_targets, result
            )
        else:
            # Multiple routing scopes — use intersection as baseline
            all_scopes = list(scope_groups.keys())
            intersection = all_scopes[0]
            for scope in all_scopes[1:]:
                intersection = intersection & scope

            # Create dial plans for intersection baseline
            if intersection:
                self._create_dial_plans(
                    store, intersection, pattern_targets, result
                )

            # Generate CSS_ROUTING_MISMATCH decisions for delta patterns
            for scope, css_ids in scope_groups.items():
                delta = scope - intersection
                if delta:
                    decision = self._create_decision(
                        store=store,
                        decision_type=DecisionType.CSS_ROUTING_MISMATCH,
                        severity="HIGH",
                        summary=(
                            f"{len(delta)} route pattern(s) in CSSes "
                            f"{css_ids} are NOT in the org-wide intersection "
                            f"baseline — these users have broader routing than "
                            f"the common baseline"
                        ),
                        context={
                            "css_ids": css_ids,
                            "reason": "routing_scope_mismatch",
                            "delta_patterns": sorted(delta),
                            "baseline_pattern_count": len(intersection),
                        },
                        options=[
                            accept_option(
                                "Include delta patterns in org-wide dial plan "
                                "(all users gain access; rely on permissions to "
                                "restrict)"
                            ),
                            accept_option(
                                "Exclude delta patterns (affected users lose "
                                "these routes)"
                            ),
                            manual_option("Admin reviews and decides per pattern"),
                        ],
                        affected_objects=css_ids,
                    )
                    store.save_decision(decision_to_store_dict(decision))
                    result.decisions.append(decision)

    def _create_dial_plans(
        self,
        store: MigrationStore,
        patterns: frozenset[str],
        pattern_targets: dict[str, tuple[str | None, str | None]],
        result: MapperResult,
    ) -> None:
        """Create CanonicalDialPlan objects from a set of route patterns.

        Groups patterns by their routing target (trunk/route group) and creates
        one dial plan per target. Patterns without a known target are grouped
        into a single 'unresolved' dial plan.

        (from 03b-transform-mappers.md §7: dial plan field mapping)
        """
        # Group patterns by target
        target_patterns: dict[tuple[str | None, str | None], list[str]] = defaultdict(
            list
        )
        for pattern in patterns:
            target = pattern_targets.get(pattern, (None, None))
            target_patterns[target].append(pattern)

        for (route_id, route_type), pat_list in target_patterns.items():
            # Convert CUCM patterns to Webex format
            webex_patterns = []
            for pat in pat_list:
                try:
                    webex_pat = cucm_to_webex_pattern(
                        pat, self.country_code, self.outside_dial_digit
                    )
                    webex_patterns.append(webex_pat)
                except (ValueError, Exception) as e:
                    logger.warning(
                        "Failed to convert pattern '%s' to Webex format: %s",
                        pat,
                        e,
                    )

            if not webex_patterns:
                continue

            # Generate dial plan name
            if route_id:
                target_name = route_id.split(":", 1)[-1] if ":" in route_id else route_id
                dp_name = f"CSS-Migration-DialPlan-{target_name}"
            else:
                dp_name = "CSS-Migration-DialPlan-Unresolved"

            dp_hash = hash_id(dp_name + "|" + ",".join(sorted(webex_patterns)))

            dial_plan = CanonicalDialPlan(
                canonical_id=f"dial_plan:css_{dp_hash}",
                provenance=Provenance(
                    source_system="cucm",
                    source_id=f"css_routing_scope",
                    source_name=dp_name,
                    extracted_at=datetime.now(timezone.utc),
                ),
                status=MigrationStatus.ANALYZED,
                name=dp_name,
                dial_patterns=sorted(set(webex_patterns)),
                route_id=route_id,
                route_type=route_type,
            )

            store.upsert_object(dial_plan)
            result.objects_created += 1

    # ------------------------------------------------------------------
    # Step 4: Compute restriction profiles
    # ------------------------------------------------------------------

    def _compute_restriction_profiles(
        self,
        store: MigrationStore,
        css_graphs: dict[str, dict[str, Any]],
        user_effective_css: dict[str, list[dict[str, Any]]],
        result: MapperResult,
    ) -> None:
        """Compute restriction profiles and create CallingPermission objects.

        For each CSS, classify block patterns into Webex categories.
        Group users by identical restriction profile (frozenset of blocked categories).
        Create one CanonicalCallingPermission per unique profile.

        (from 04-css-decomposition.md Step 4)
        """
        # Compute restriction profile per CSS
        css_restriction_profiles: dict[str, frozenset[str]] = {}
        css_unclassified: dict[str, list[str]] = {}

        for css_id, graph in css_graphs.items():
            blocked_categories: set[str] = set()
            unclassified_patterns: list[str] = []

            for partition in graph["partitions"]:
                if partition["classification"] == BLOCKING:
                    for pat in partition["patterns"]:
                        if pat["action"] == "BLOCK":
                            category = classify_block_pattern(
                                pat["pattern"], self.category_rules
                            )
                            if category:
                                blocked_categories.add(category)
                            else:
                                unclassified_patterns.append(pat["pattern"])

            css_restriction_profiles[css_id] = frozenset(blocked_categories)
            if unclassified_patterns:
                css_unclassified[css_id] = unclassified_patterns

        # Generate CALLING_PERMISSION_MISMATCH decisions for unclassifiable patterns
        for css_id, patterns in css_unclassified.items():
            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.CALLING_PERMISSION_MISMATCH,
                severity="MEDIUM",
                summary=(
                    f"CSS '{css_id}' has {len(patterns)} block pattern(s) "
                    f"that cannot be classified into Webex permission categories: "
                    f"{patterns}"
                ),
                context={
                    "css_id": css_id,
                    "reason": "unclassifiable_block_patterns",
                    "unclassified_patterns": patterns,
                },
                options=[
                    accept_option(
                        "Accept that these blocking restrictions are lost in migration"
                    ),
                    manual_option(
                        "Admin maps patterns to Webex categories or implements "
                        "custom blocking dial plan routes"
                    ),
                    skip_option(
                        "Skip restriction — affected users get unrestricted access "
                        "for these call types"
                    ),
                ],
                affected_objects=[css_id],
            )
            store.save_decision(decision_to_store_dict(decision))
            result.decisions.append(decision)

        # Group users by identical restriction profile.
        # Use user_effective_css (includes line/device CSS fallback users),
        # not just user_has_css cross-refs, so that users inheriting CSS
        # via line or device also get calling permissions assigned.
        profile_users: dict[frozenset[str], list[str]] = defaultdict(list)
        for user_id, partitions in user_effective_css.items():
            # Compute this user's restriction profile from their effective
            # blocking partitions (same logic as per-CSS, but user-specific)
            user_blocked: set[str] = set()
            for pt_info in partitions:
                if pt_info.get("classification") != "BLOCKING":
                    continue
                for pat in pt_info.get("patterns", []):
                    cat = classify_block_pattern(
                        pat["pattern"], self.category_rules
                    )
                    if cat:
                        user_blocked.add(cat)
            profile = frozenset(user_blocked)
            profile_users[profile].append(user_id)

        # Also add users from CSSes that have no users mapped via cross-refs
        # (the profile still needs to be created)

        # Create one CanonicalCallingPermission per unique restriction profile
        for profile_idx, (blocked_categories, users) in enumerate(
            profile_users.items()
        ):
            # Deduplicate users
            unique_users = sorted(set(users))

            # Skip orphaned profiles — no users reference this CSS
            if not unique_users:
                logger.debug(
                    "Skipping orphaned calling permission profile "
                    "(categories: %s) — 0 users assigned",
                    ",".join(sorted(blocked_categories)) if blocked_categories else "allow_all",
                )
                continue

            # Build the callingPermissions array
            # All Webex call types get an entry; blocked categories get BLOCK action
            permissions = []
            for call_type in WEBEX_CALL_TYPES:
                # Map our category names to Webex call type names
                is_blocked = self._category_matches_call_type(
                    blocked_categories, call_type
                )
                permissions.append(
                    CallingPermissionEntry(
                        call_type=call_type,
                        action="BLOCK" if is_blocked else "ALLOW",
                        transfer_enabled=not is_blocked,
                    )
                )

            profile_hash = hash_id(
                ",".join(sorted(blocked_categories)) if blocked_categories else "allow_all"
            )

            permission = CanonicalCallingPermission(
                canonical_id=f"calling_permission:{profile_hash}",
                provenance=Provenance(
                    source_system="cucm",
                    source_id=f"css_restriction_profile_{profile_idx}",
                    source_name=(
                        f"Restriction-{','.join(sorted(blocked_categories))}"
                        if blocked_categories
                        else "Allow-All"
                    ),
                    extracted_at=datetime.now(timezone.utc),
                ),
                status=MigrationStatus.ANALYZED,
                calling_permissions=permissions,
                assigned_users=unique_users,
                use_custom_enabled=bool(blocked_categories),
                use_custom_permissions=bool(blocked_categories),
            )

            store.upsert_object(permission)
            result.objects_created += 1

    @staticmethod
    def _category_matches_call_type(
        blocked_categories: frozenset[str],
        call_type: str,
    ) -> bool:
        """Check if a Webex call type should be blocked based on blocked categories.

        Maps the configurable category names (from category_rules) to Webex
        OutgoingPermissionCallType enum values.

        (from 03b-transform-mappers.md §7: callingPermissions field mapping)
        """
        # Mapping from our category names to Webex call type names
        # This is configurable via category_rules — the webex_category values
        # in the rules should match these keys.
        category_to_call_type: dict[str, list[str]] = {
            "international": ["INTERNATIONAL"],
            "premium": ["PREMIUM_SERVICES_I", "PREMIUM_SERVICES_II"],
            "operator": ["OPERATOR_ASSISTED"],
            "directory_assistance": ["CHARGEABLE_DIRECTORY_ASSISTED"],
            "toll_free": ["TOLL_FREE"],
            "national": ["NATIONAL"],
            "special_services": ["SPECIAL_SERVICES_I", "SPECIAL_SERVICES_II"],
            "internal": ["INTERNAL_CALL"],
        }

        for category in blocked_categories:
            mapped_types = category_to_call_type.get(category, [])
            if call_type in mapped_types:
                return True

        return False

    # ------------------------------------------------------------------
    # Step 5: Detect ordering conflicts
    # ------------------------------------------------------------------

    def _detect_ordering_conflicts(
        self,
        store: MigrationStore,
        css_graphs: dict[str, dict[str, Any]],
        result: MapperResult,
    ) -> None:
        """Detect cases where CUCM partition ordering produces different behavior
        than Webex's independent routing+permissions model.

        (from 04-css-decomposition.md Step 5)
        """
        for css_id, graph in css_graphs.items():
            # Collect all patterns with their action and ordinal, sorted by ordinal
            all_patterns: list[tuple[str, str, int]] = []
            for partition in graph["partitions"]:
                for pat in partition["patterns"]:
                    if pat["action"] in ("ROUTE", "BLOCK"):
                        all_patterns.append(
                            (pat["pattern"], pat["action"], partition["ordinal"])
                        )

            # Sort by ordinal (priority order)
            all_patterns.sort(key=lambda x: x[2])

            # Check each pair where a higher-priority pattern shadows a lower one
            for i, (pat_a, action_a, prio_a) in enumerate(all_patterns):
                for pat_b, action_b, prio_b in all_patterns[i + 1 :]:
                    if action_a == action_b:
                        continue  # Same action, no conflict
                    if not cucm_patterns_overlap(pat_a, pat_b):
                        continue  # No overlap, no shadowing

                    # Determine risk
                    if action_a == "ROUTE" and action_b == "BLOCK":
                        risk = "Webex MORE restrictive than CUCM"
                        cucm_behavior = (
                            f"ALLOWED (route '{pat_a}' at priority {prio_a} "
                            f"shadows block '{pat_b}' at priority {prio_b})"
                        )
                        webex_behavior = (
                            "BLOCKED (permissions enforced independently of routing)"
                        )
                        severity = "MEDIUM"
                    elif action_a == "BLOCK" and action_b == "ROUTE":
                        risk = "Webex LESS restrictive than CUCM"
                        cucm_behavior = (
                            f"BLOCKED (block '{pat_a}' at priority {prio_a} "
                            f"shadows route '{pat_b}' at priority {prio_b})"
                        )
                        webex_behavior = (
                            "ALLOWED (dial plan routes, no matching permission block)"
                        )
                        severity = "HIGH"  # LESS restrictive is riskier
                    else:
                        continue

                    decision = self._create_decision(
                        store=store,
                        decision_type=DecisionType.CSS_ROUTING_MISMATCH,
                        severity=severity,
                        summary=(
                            f"Ordering conflict in CSS '{css_id}': "
                            f"{risk}. CUCM: {cucm_behavior}. "
                            f"Webex: {webex_behavior}."
                        ),
                        context={
                            "css_id": css_id,
                            "reason": "ordering_conflict",
                            "shadowing_pattern": pat_a,
                            "shadowed_pattern": pat_b,
                            "shadowing_action": action_a,
                            "shadowed_action": action_b,
                            "shadowing_priority": prio_a,
                            "shadowed_priority": prio_b,
                            "risk": risk,
                            "cucm_behavior": cucm_behavior,
                            "webex_behavior": webex_behavior,
                        },
                        options=[
                            accept_option(
                                f"Accept Webex behavior ({risk})"
                            ),
                            manual_option(
                                "Admin adjusts permissions to compensate "
                                "for ordering difference"
                            ),
                        ],
                        affected_objects=[css_id],
                    )
                    store.save_decision(decision_to_store_dict(decision))
                    result.decisions.append(decision)


