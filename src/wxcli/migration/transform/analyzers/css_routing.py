"""CSS routing analyzer — finds overlapping/conflicting dial plan patterns.

The css_mapper produces CanonicalDialPlan objects and CSS_ROUTING_MISMATCH
decisions when it detects routing scope differences between CSSes assigned to
users.  This analyzer performs a cross-object sweep to find routing mismatches
NOT covered by the mapper — specifically, dial_plan objects that contain
conflicting or overlapping patterns (same pattern pointing to different routes).

Decision ownership: MAPPER-OWNED (css_mapper produces CSS_ROUTING_MISMATCH).
This analyzer checks for existing mapper decisions before creating new ones.

(from 03-conflict-detection-engine.md, CSS routing conflict detection)
(from 03b-transform-mappers.md, css_mapper dial plan routing)
(from 07-idempotency-resumability.md, fingerprint-based identity)
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


class CSSRoutingAnalyzer(Analyzer):
    """Finds conflicting dial plan patterns across CSS routing scopes.

    CUCM allows the same dial pattern to appear in multiple dial plans
    pointing to different routes (separated by CSS scope).  When these
    are flattened for Webex Calling, overlapping patterns with different
    routes create ambiguity.

    The css_mapper may already have produced CSS_ROUTING_MISMATCH decisions
    for some dial plans.  This analyzer only creates decisions for conflicts
    that the mapper missed, acting as a cross-object safety net.
    """

    name = "css_routing"
    decision_types = [DecisionType.CSS_ROUTING_MISMATCH]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep all dial_plan objects, find overlapping patterns with different routes."""
        decisions: list[Decision] = []

        # Step 1: Get existing mapper-produced CSS_ROUTING_MISMATCH decisions
        existing = self._get_existing_decisions_for_type(
            store, DecisionType.CSS_ROUTING_MISMATCH
        )

        # Step 2: Load all dial_plan objects
        dial_plans = store.get_objects("dial_plan")
        if not dial_plans:
            return decisions

        # Step 3: Build a map of pattern → [(dial_plan_id, route_id)]
        # CanonicalDialPlan.dial_patterns is list[str] and route_id is a
        # top-level field on the dial plan object.  Each dial plan maps all
        # its patterns to the same route.
        # (from models.py: CanonicalDialPlan.dial_patterns: list[str],
        #  route_id: str, route_type: str)
        pattern_routes: dict[str, list[dict[str, str]]] = defaultdict(list)

        dial_plan_by_id: dict[str, dict[str, Any]] = {}
        for dp in dial_plans:
            dp_id = dp.get("canonical_id", "")
            if not dp_id:
                continue
            dial_plan_by_id[dp_id] = dp

            route_id = dp.get("route_id", "") or ""
            dp_patterns = dp.get("dial_patterns", [])
            for pattern in dp_patterns:
                # dial_patterns is list[str] — each entry is a pattern string
                if isinstance(pattern, str) and pattern:
                    pattern_routes[pattern].append({
                        "dial_plan_id": dp_id,
                        "route_id": route_id,
                    })

        # Step 4: Find patterns that appear in multiple dial plans with different routes
        for pattern, entries in sorted(pattern_routes.items()):
            if len(entries) < 2:
                continue

            # Check if routes actually differ
            unique_routes = set(e["route_id"] for e in entries)
            if len(unique_routes) < 2:
                continue  # Same route everywhere — no conflict

            # Collect the dial_plan IDs involved in this conflict
            involved_dp_ids = sorted(set(e["dial_plan_id"] for e in entries))

            # Skip if ALL involved dial plans already have mapper decisions
            all_covered = all(dp_id in existing for dp_id in involved_dp_ids)
            if all_covered:
                continue

            # Build scope description from dial plan names
            scope_parts = []
            for dp_id in involved_dp_ids:
                dp_data = dial_plan_by_id.get(dp_id, {})
                dp_name = dp_data.get("name", dp_id)
                route_ids_for_dp = [
                    e["route_id"] for e in entries if e["dial_plan_id"] == dp_id
                ]
                scope_parts.append(
                    f"{dp_name} -> {', '.join(route_ids_for_dp)}"
                )

            context = {
                "dial_plan_ids": involved_dp_ids,
                "conflicting_pattern": pattern,
                "route_entries": entries,
                "scope_description": "; ".join(scope_parts),
            }

            options = [
                DecisionOption(
                    id="use_union",
                    label="Union All Routing Scopes",
                    impact=(
                        f"Merge routing for pattern '{pattern}' across "
                        f"{len(involved_dp_ids)} dial plans — all routes reachable"
                    ),
                ),
                DecisionOption(
                    id="use_intersection",
                    label="Most Restrictive Scope",
                    impact=(
                        f"Keep only routes common to all dial plans for "
                        f"pattern '{pattern}' — most restrictive"
                    ),
                ),
                DecisionOption(
                    id="manual",
                    label="Manual Resolution",
                    impact=(
                        f"Manually configure routing for pattern '{pattern}' "
                        f"in Webex Calling"
                    ),
                ),
                DecisionOption(
                    id="skip",
                    label="Skip",
                    impact=(
                        f"Leave pattern '{pattern}' unresolved — "
                        f"manual intervention required"
                    ),
                ),
            ]

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.CSS_ROUTING_MISMATCH,
                severity="HIGH",
                summary=(
                    f"Pattern '{pattern}' routes to {len(unique_routes)} "
                    f"different destinations across {len(involved_dp_ids)} "
                    f"dial plans"
                ),
                context=context,
                options=options,
                affected_objects=involved_dp_ids,
            )
            decisions.append(decision)

        # Step 5: Check for user CSS assignments with divergent routing scopes
        # Query cross_refs for user_has_css to find users grouped by CSS
        css_rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'user_has_css'"
        ).fetchall()

        if css_rows:
            # Group users by CSS
            css_to_users: dict[str, list[str]] = defaultdict(list)
            for row in css_rows:
                css_to_users[row["to_id"]].append(row["from_id"])

            # For each pair of CSSes, check if they reference dial plans with conflicting routes
            css_ids = sorted(css_to_users.keys())
            css_dial_plans: dict[str, set[str]] = defaultdict(set)

            # Get CSS → dial_plan cross_refs
            css_dp_rows = store.conn.execute(
                "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'css_has_dial_plan'"
            ).fetchall()
            for row in css_dp_rows:
                css_dial_plans[row["from_id"]].add(row["to_id"])

            # Compare routing scopes between CSSes that have users
            # Two CSSes with different dial plan memberships assigned to users
            # in the same location indicate a routing scope mismatch
            user_objects = store.get_objects("user")
            user_location: dict[str, str] = {}
            for user in user_objects:
                uid = user.get("canonical_id", "")
                loc = user.get("location_id", "")  # CanonicalUser.location_id
                if uid and loc:
                    user_location[uid] = loc

            # Group CSSes by location (via their assigned users)
            location_csses: dict[str, set[str]] = defaultdict(set)
            for css_id, user_ids in css_to_users.items():
                for uid in user_ids:
                    loc = user_location.get(uid)
                    if loc:
                        location_csses[loc].add(css_id)

            # For each location with multiple CSSes, check for dial plan divergence
            for loc_id, loc_css_ids in sorted(location_csses.items()):
                if len(loc_css_ids) < 2:
                    continue

                loc_css_list = sorted(loc_css_ids)
                # Compute the set of dial plans for each CSS
                dp_sets = {
                    css_id: css_dial_plans.get(css_id, set())
                    for css_id in loc_css_list
                }

                # Find CSSes with non-identical dial plan sets
                unique_dp_combos = set(
                    frozenset(dps) for dps in dp_sets.values()
                )
                if len(unique_dp_combos) < 2:
                    continue  # All CSSes in this location have the same dial plans

                all_css_dp_ids = sorted(
                    set().union(*(dps for dps in dp_sets.values()))
                )

                # Skip if all involved objects already have mapper decisions
                all_covered = all(
                    dp_id in existing for dp_id in all_css_dp_ids
                ) and all(
                    css_id in existing for css_id in loc_css_list
                )
                if all_covered:
                    continue

                css_scope_desc = []
                for css_id in loc_css_list:
                    dps = sorted(dp_sets.get(css_id, set()))
                    user_count = len(css_to_users.get(css_id, []))
                    css_scope_desc.append(
                        f"CSS {css_id} ({user_count} users): "
                        f"dial_plans=[{', '.join(dps)}]"
                    )

                scope_context = {
                    "dial_plan_ids": all_css_dp_ids,
                    "css_ids": loc_css_list,
                    "location_id": loc_id,
                    "scope_description": "; ".join(css_scope_desc),
                }

                scope_options = [
                    DecisionOption(
                        id="use_union",
                        label="Union All Routing Scopes",
                        impact=(
                            f"Merge all {len(all_css_dp_ids)} dial plans into a "
                            f"single routing scope for location {loc_id}"
                        ),
                    ),
                    DecisionOption(
                        id="use_intersection",
                        label="Most Restrictive Scope",
                        impact=(
                            f"Use only dial plans common to all CSSes in "
                            f"location {loc_id}"
                        ),
                    ),
                    DecisionOption(
                        id="manual",
                        label="Manual Resolution",
                        impact=(
                            f"Manually configure routing for users in "
                            f"location {loc_id}"
                        ),
                    ),
                    DecisionOption(
                        id="skip",
                        label="Skip",
                        impact="Leave routing scope divergence unresolved",
                    ),
                ]

                affected = sorted(set(all_css_dp_ids + loc_css_list))

                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.CSS_ROUTING_MISMATCH,
                    severity="HIGH",
                    summary=(
                        f"{len(loc_css_list)} CSSes in location {loc_id} have "
                        f"divergent routing scopes ({len(all_css_dp_ids)} "
                        f"dial plans involved)"
                    ),
                    context=scope_context,
                    options=scope_options,
                    affected_objects=affected,
                )
                decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from dial plan IDs and conflicting pattern details.

        Includes:
        - sorted dial_plan canonical_ids
        - conflicting_pattern (if present — pattern-level conflict)
        - css_ids + location_id (if present — scope-level conflict)

        (from 07-idempotency-resumability.md lines 30-43)
        """
        data: dict[str, Any] = {
            "type": decision_type.value,
            "dial_plan_ids": sorted(context.get("dial_plan_ids", [])),
        }

        # Pattern-level conflict
        if "conflicting_pattern" in context:
            data["conflicting_pattern"] = context["conflicting_pattern"]

        # Scope-level conflict (CSS divergence)
        if "css_ids" in context:
            data["css_ids"] = sorted(context["css_ids"])
            data["location_id"] = context.get("location_id")

        return self._hash_fingerprint(data)
