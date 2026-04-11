"""Routing mapper: CUCM routing infrastructure -> Webex Calling routing.

Maps CUCM SIP Trunks/Gateways, Route Groups, Route Patterns (-> Dial Plans),
and Translation Patterns to Webex Calling routing objects.

(from 03b-transform-mappers.md §6, routing_mapper)

Cross-ref reads:
    route_pattern_uses_gateway      (#11) — MAY be empty (listRoutePattern limitation)
    route_pattern_uses_route_list   (#12) — MAY be empty (listRoutePattern limitation)
    route_group_has_trunk           (#13) — route group membership
    trunk_at_location               (#14) — trunk -> device pool for location
    translation_pattern_in_partition (#15) — translation pattern scoping

Decisions generated:
    FEATURE_APPROXIMATION  — @ macro in route pattern
    LOCATION_AMBIGUOUS     — trunk has no device pool; multiple locations available
    MISSING_DATA           — trunk password, missing address, partition scope issues
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.models import (
    CanonicalDialPlan,
    CanonicalRouteGroup,
    CanonicalRouteList,
    CanonicalTranslationPattern,
    CanonicalTrunk,
    DecisionOption,
    DecisionType,
    MapperResult,
    MigrationStatus,
    Provenance,
    TrunkGatewayRef,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    decision_to_store_dict,
    extract_provenance,
    hash_id,
    manual_option,
    skip_option,
)
from wxcli.migration.transform.pattern_converter import cucm_to_webex_pattern

logger = logging.getLogger(__name__)

# Max trunks per Webex route group
# (from 03b-transform-mappers.md §6: "Max 10 trunks per route group in Webex")
_MAX_TRUNKS_PER_ROUTE_GROUP = 10

# Temporary password length for trunk authentication
_TRUNK_PASSWORD_LENGTH = 16


def _bool_field(val: Any) -> bool | None:
    """Coerce an AXL field to bool or None."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).lower()
    if s in ("true", "t", "1"):
        return True
    if s in ("false", "f", "0"):
        return False
    return None


def _generate_temp_password() -> str:
    """Generate a temporary password for trunk authentication.

    (from 03b-transform-mappers.md §6: "mapper generates a temporary password")
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(_TRUNK_PASSWORD_LENGTH))


class RoutingMapper(Mapper):
    """Maps CUCM routing infrastructure to Webex Calling routing objects.

    Produces: CanonicalTrunk, CanonicalRouteGroup, CanonicalDialPlan,
    CanonicalTranslationPattern.

    (from 03b-transform-mappers.md §6)
    """

    name = "routing_mapper"
    depends_on = ["location_mapper"]

    def __init__(
        self,
        country_code: str = "+1",
        outside_dial_digit: str = "9",
    ) -> None:
        self.country_code = country_code
        self.outside_dial_digit = outside_dial_digit

    def map(self, store: MigrationStore) -> MapperResult:
        """Read routing objects and produce Webex routing canonical objects."""
        result = MapperResult()

        self._map_trunks(store, result)
        self._map_route_groups(store, result)
        self._map_route_lists(store, result)
        self._map_dial_plans(store, result)
        self._map_translation_patterns(store, result)

        return result

    # ------------------------------------------------------------------
    # Trunks: CUCM SIP Trunk / Gateway -> CanonicalTrunk
    # ------------------------------------------------------------------

    def _map_trunks(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM SIP trunks and gateways to CanonicalTrunk objects.

        (from 03b-transform-mappers.md §6: trunk field mapping table)
        """
        for trunk_type in ("sip_trunk", "gateway"):
            for trunk_data in store.get_objects(trunk_type):
                trunk_id = trunk_data["canonical_id"]
                state = trunk_data.get("pre_migration_state") or {}

                name = state.get("name") or trunk_id.split(":", 1)[-1]

                # --- Location resolution ---
                # Chain: trunk -> trunk_at_location -> device_pool -> device_pool_to_location
                # (from 03b-transform-mappers.md §6: "trunk_at_location cross-ref")
                location_id = store.resolve_chain(
                    trunk_id, "trunk_at_location", "device_pool_to_location"
                )

                # --- Trunk type inference ---
                # (from 03b-transform-mappers.md §6: "SIP profile + security profile -> type")
                trunk_type_val = _infer_trunk_type(state)

                # --- Destination address ---
                # Phase 04 correction: destinations is a LIST of [{address, port, sort_order}]
                # Use primary destination (sort_order 1 or first in list)
                address = None
                port = None
                destinations = state.get("destinations", [])
                if isinstance(destinations, list) and destinations:
                    # Find primary destination (sort_order 1 or first)
                    primary = destinations[0] or {}
                    for dest in destinations:
                        if not dest:
                            continue
                        if dest.get("sort_order") == 1:
                            primary = dest
                            break
                    address = primary.get("address")
                    port = primary.get("port")
                elif isinstance(destinations, dict):
                    # Legacy flat format fallback
                    address = destinations.get("address") or state.get("destination_address")
                    port = destinations.get("port") or state.get("destination_port")
                else:
                    # Try flat fields as last resort
                    address = state.get("destination_address")
                    port = state.get("destination_port")

                if port is not None:
                    try:
                        port = int(port)
                    except (ValueError, TypeError):
                        port = None

                # --- Password generation ---
                # (from 03b-transform-mappers.md §6: "mapper generates temporary password")
                password = _generate_temp_password()

                # --- Max concurrent calls ---
                max_concurrent_calls = state.get("max_calls") or state.get("maxCallsPerSIPTrunk")
                if max_concurrent_calls is not None:
                    try:
                        max_concurrent_calls = int(max_concurrent_calls)
                    except (ValueError, TypeError):
                        max_concurrent_calls = None

                # --- Other fields ---
                dual_identity = state.get("dualIdentitySupportEnabled")
                device_type = state.get("device_type")
                p_charge_info = state.get("pChargeInfoSupportPolicy")

                # Fix 10: Resolve location when cross-ref chain breaks (org-wide trunks)
                if not location_id:
                    locations = store.get_objects("location")
                    if len(locations) == 1:
                        # Single location — auto-assign (no decision needed)
                        location_id = locations[0]["canonical_id"]
                        logger.info(
                            "Trunk '%s' auto-assigned to only location '%s'",
                            name, location_id,
                        )
                    elif len(locations) > 1:
                        # Multiple locations — present as selectable options
                        loc_options = [
                            DecisionOption(
                                id=loc["canonical_id"],
                                label=f"Assign to {(loc.get('pre_migration_state') or {}).get('name', loc['canonical_id'])}",
                                impact=f"Trunk created in {(loc.get('pre_migration_state') or {}).get('name', loc['canonical_id'])}",
                            )
                            for loc in locations
                        ]
                        loc_options.append(skip_option("Trunk not migrated"))
                        decision = self._create_decision(
                            store=store,
                            decision_type=DecisionType.LOCATION_AMBIGUOUS,
                            severity="HIGH",
                            summary=(
                                f"Trunk '{name}' has no device pool — "
                                f"choose which of {len(locations)} locations to assign it to"
                            ),
                            context={
                                "trunk_id": f"trunk:{name}",
                                "trunk_name": name,
                                "reason": "no_location",
                                "available_locations": [
                                    loc["canonical_id"] for loc in locations
                                ],
                            },
                            options=loc_options,
                            affected_objects=[f"trunk:{name}"],
                        )
                        store.save_decision(decision_to_store_dict(decision))
                        result.decisions.append(decision)
                    else:
                        # No locations at all — MISSING_DATA
                        decision = self._create_decision(
                            store=store,
                            decision_type=DecisionType.MISSING_DATA,
                            severity="HIGH",
                            summary=(
                                f"Trunk '{name}' has no resolvable location and "
                                f"no locations exist in migration — "
                                f"locationId required for Webex trunk creation"
                            ),
                            context={
                                "trunk_id": f"trunk:{name}",
                                "trunk_name": name,
                                "reason": "no_location",
                            },
                            options=[
                                manual_option("Admin assigns trunk to a Webex location"),
                                skip_option("Trunk not migrated"),
                            ],
                            affected_objects=[f"trunk:{name}"],
                        )
                        store.save_decision(decision_to_store_dict(decision))
                        result.decisions.append(decision)

                trunk = CanonicalTrunk(
                    canonical_id=f"trunk:{name}",
                    provenance=extract_provenance(trunk_data),
                    status=MigrationStatus.ANALYZED,
                    name=name,
                    location_id=location_id,
                    trunk_type=trunk_type_val,
                    address=address,
                    domain=state.get("domain"),
                    port=port,
                    max_concurrent_calls=max_concurrent_calls,
                    password=password,
                    dual_identity_support_enabled=dual_identity,
                    device_type=device_type,
                    p_charge_info_support_policy=p_charge_info,
                    # Tier 2 §2.8: SIP/security profile detail
                    sip_profile_early_offer=_bool_field(state.get("sip_profile_early_offer")),
                    sip_profile_srtp_fallback=_bool_field(state.get("sip_profile_srtp_fallback")),
                    security_mode=state.get("security_mode"),
                    security_digest_auth=_bool_field(state.get("security_digest_auth")),
                )

                store.upsert_object(trunk)
                result.objects_created += 1

                # --- MISSING_DATA decision for password ---
                # (from 03b-transform-mappers.md §6: "trunk password can't be extracted")
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary=(
                        f"Trunk '{name}' password cannot be extracted from CUCM — "
                        f"temporary password generated"
                    ),
                    context={
                        "trunk_id": trunk.canonical_id,
                        "trunk_name": name,
                        "reason": "password_not_extractable",
                    },
                    options=[
                        manual_option(
                            "Admin configures matching passwords on gateway and in Webex"
                        ),
                        accept_option(
                            "Accept generated password and update gateway configuration"
                        ),
                    ],
                    affected_objects=[trunk.canonical_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

                # --- MISSING_DATA decision for missing address ---
                if not address and trunk_type_val == "CERTIFICATE_BASED":
                    decision = self._create_decision(
                        store=store,
                        decision_type=DecisionType.MISSING_DATA,
                        severity="HIGH",
                        summary=(
                            f"Trunk '{name}' has no destination address — "
                            f"required for CERTIFICATE_BASED trunk type"
                        ),
                        context={
                            "trunk_id": trunk.canonical_id,
                            "trunk_name": name,
                            "reason": "missing_address",
                        },
                        options=[
                            manual_option("Admin provides SBC/gateway FQDN or SRV record"),
                            skip_option("Skip trunk — routing through this trunk won't be migrated"),
                        ],
                        affected_objects=[trunk.canonical_id],
                    )
                    store.save_decision(decision_to_store_dict(decision))
                    result.decisions.append(decision)

    # ------------------------------------------------------------------
    # Route Groups: CUCM Route Group -> CanonicalRouteGroup
    # ------------------------------------------------------------------

    def _map_route_groups(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM route groups to CanonicalRouteGroup objects.

        Splits groups exceeding 10-trunk limit into multiple Webex route groups.

        (from 03b-transform-mappers.md §6: route group field mapping table)
        """
        for rg_data in store.get_objects("route_group"):
            rg_id = rg_data["canonical_id"]
            state = rg_data.get("pre_migration_state") or {}

            rg_name = state.get("name") or rg_id.split(":", 1)[-1]

            # --- Resolve trunks via cross-ref ---
            # (from 03b-transform-mappers.md §6: "route_group_has_trunk")
            trunk_refs = store.find_cross_refs(rg_id, "route_group_has_trunk")

            # Build trunk gateway refs with priority from pre_migration_state
            trunks_with_priority = []
            state_trunks = state.get("trunks") or []
            for i, trunk_ref_id in enumerate(trunk_refs):
                # Try to find priority from state data
                priority = i + 1
                trunk_name = trunk_ref_id.split(":", 1)[-1] if ":" in trunk_ref_id else trunk_ref_id
                for st in state_trunks:
                    if not st:
                        continue
                    if st.get("trunk_name") == trunk_name:
                        priority = st.get("priority", i + 1)
                        break

                # Resolve to the canonical trunk ID (trunk:name format)
                canonical_trunk_id = f"trunk:{trunk_name}"
                trunks_with_priority.append(
                    TrunkGatewayRef(trunk_canonical_id=canonical_trunk_id, priority=priority)
                )

            # Fix 11: MISSING_DATA decision if no gateways resolved
            if not trunks_with_priority:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="HIGH",
                    summary=(
                        f"Route group '{rg_name}' has no resolvable gateway members — "
                        f"at least one localGateway required"
                    ),
                    context={
                        "route_group_id": f"route_group:{rg_name}",
                        "route_group_name": rg_name,
                        "reason": "no_gateways",
                    },
                    options=[
                        manual_option("Admin assigns trunk/gateway members"),
                        skip_option("Route group not migrated"),
                    ],
                    affected_objects=[f"route_group:{rg_name}"],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            # --- Split if exceeding max trunks ---
            # (from 03b-transform-mappers.md §6: "Max 10 trunks per route group")
            if len(trunks_with_priority) <= _MAX_TRUNKS_PER_ROUTE_GROUP:
                rg = CanonicalRouteGroup(
                    canonical_id=f"route_group:{rg_name}",
                    provenance=extract_provenance(rg_data),
                    status=MigrationStatus.ANALYZED,
                    name=rg_name,
                    local_gateways=trunks_with_priority,
                )
                store.upsert_object(rg)
                result.objects_created += 1
            else:
                # Split into chunks of max 10
                for chunk_idx, start in enumerate(
                    range(0, len(trunks_with_priority), _MAX_TRUNKS_PER_ROUTE_GROUP)
                ):
                    chunk = trunks_with_priority[start:start + _MAX_TRUNKS_PER_ROUTE_GROUP]
                    split_name = f"{rg_name}-{chunk_idx + 1}"
                    rg = CanonicalRouteGroup(
                        canonical_id=f"route_group:{split_name}",
                        provenance=extract_provenance(rg_data),
                        status=MigrationStatus.ANALYZED,
                        name=split_name,
                        local_gateways=chunk,
                    )
                    store.upsert_object(rg)
                    result.objects_created += 1

    # ------------------------------------------------------------------
    # Route Lists: CUCM Route List -> CanonicalRouteList
    # ------------------------------------------------------------------

    def _map_route_lists(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM route lists to CanonicalRouteList objects.

        Webex route lists bind to exactly ONE route group. CUCM route lists with
        multiple route group members produce a FEATURE_APPROXIMATION decision.
        Route lists are standalone resources — dial plans point to route groups,
        not route lists (RouteType enum = ROUTE_GROUP | TRUNK only).
        """
        for rl_data in store.get_objects("route_list"):
            if rl_data.get("status") == "analyzed":
                continue  # Already mapped (e.g., re-run)

            rl_id = rl_data["canonical_id"]
            state = rl_data.get("pre_migration_state") or {}
            rl_name = state.get("route_list_name") or rl_id.split(":", 1)[-1]

            # Skip disabled route lists
            enabled = state.get("routeListEnabled", "true")
            if str(enabled).lower() == "false":
                continue

            route_groups = state.get("route_groups") or []

            # No route group members -> MISSING_DATA
            if not route_groups:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="HIGH",
                    summary=(
                        f"Route list '{rl_name}' has no route group members — "
                        f"at least one route group required"
                    ),
                    context={
                        "route_list_id": rl_id,
                        "route_list_name": rl_name,
                        "reason": "route_list_no_members",
                    },
                    options=[
                        manual_option("Admin assigns route group member"),
                        skip_option("Route list not migrated"),
                    ],
                    affected_objects=[rl_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
                continue

            # Single route group -> direct mapping
            if len(route_groups) == 1:
                rg_name = route_groups[0]
                rl = CanonicalRouteList(
                    canonical_id=rl_id,
                    provenance=extract_provenance(rl_data),
                    status=MigrationStatus.ANALYZED,
                    name=rl_name,
                    route_group_id=f"route_group:{rg_name}",
                    cucm_route_list_name=rl_name,
                    cucm_route_groups=route_groups,
                )
                store.upsert_object(rl)
                result.objects_created += 1
            else:
                # Multiple route groups -> FEATURE_APPROXIMATION decision
                # Webex route lists bind to exactly ONE route group
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="MEDIUM",
                    summary=(
                        f"Route list '{rl_name}' has {len(route_groups)} route group members "
                        f"({', '.join(route_groups)}). Webex route lists bind to exactly one "
                        f"route group — choose how to handle the extra members."
                    ),
                    context={
                        "route_list_id": rl_id,
                        "route_list_name": rl_name,
                        "route_groups": route_groups,
                        "reason": "multi_route_group_route_list",
                    },
                    options=[
                        accept_option(
                            f"Split into {len(route_groups)} route lists "
                            f"(one per route group)"
                        ),
                        accept_option(
                            f"Use first route group only ({route_groups[0]}) — "
                            f"loses failover to other members"
                        ),
                        skip_option("Route list not migrated"),
                    ],
                    affected_objects=[rl_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

                # Default: create with first route group (can be overridden by decision)
                rl = CanonicalRouteList(
                    canonical_id=rl_id,
                    provenance=extract_provenance(rl_data),
                    status=MigrationStatus.ANALYZED,
                    name=rl_name,
                    route_group_id=f"route_group:{route_groups[0]}",
                    cucm_route_list_name=rl_name,
                    cucm_route_groups=route_groups,
                )
                store.upsert_object(rl)
                result.objects_created += 1

    # ------------------------------------------------------------------
    # Dial Plans: CUCM Route Patterns -> CanonicalDialPlan
    # ------------------------------------------------------------------

    def _map_dial_plans(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM route patterns to CanonicalDialPlan objects.

        Groups route patterns by their routing target (gateway/trunk or route group)
        into consolidated dial plans.

        Phase 04 correction: route_pattern_uses_gateway (#11) and
        route_pattern_uses_route_list (#12) cross-refs may be EMPTY because
        listRoutePattern doesn't return destination data. Must fall back to
        pre_migration_state if available.

        (from 03b-transform-mappers.md §6: dial plan field mapping table)
        """
        # Group patterns by target for consolidation
        # Key = target canonical_id (trunk:X or route_group:X), Value = list of converted patterns
        target_groups: dict[str, list[str]] = {}
        # Track route pattern names for dial plan naming
        target_names: dict[str, str] = {}
        # Track route types per target
        target_route_types: dict[str, str] = {}

        rp_count = 0
        skipped_at_macro = 0
        skipped_no_target = 0

        for rp_data in store.get_objects("route_pattern"):
            rp_id = rp_data["canonical_id"]
            state = rp_data.get("pre_migration_state") or {}

            cucm_pattern = state.get("pattern", "")

            # --- @ macro detection ---
            # (from 03b-transform-mappers.md §6: "@ macro requires expansion")
            if "@" in cucm_pattern:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="MEDIUM",
                    summary=(
                        f"Route pattern '{cucm_pattern}' uses @ macro (national numbering "
                        f"plan) which has no single Webex equivalent"
                    ),
                    context={
                        "route_pattern_id": rp_id,
                        "cucm_pattern": cucm_pattern,
                        "reason": "at_macro",
                    },
                    options=[
                        accept_option("Expand to explicit pattern set from national plan"),
                        accept_option("Use broad wildcard +! as approximation"),
                        manual_option("Admin defines explicit patterns manually"),
                    ],
                    affected_objects=[rp_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
                # Skip this pattern — can't convert automatically
                skipped_at_macro += 1
                continue

            # --- Convert pattern ---
            webex_pattern = cucm_to_webex_pattern(
                cucm_pattern, self.country_code, self.outside_dial_digit
            )

            # --- Resolve routing target ---
            # Try cross-refs first, then fall back to pre_migration_state
            # Phase 04 correction: cross-refs may be empty
            target_id = None
            route_type = None

            # Try gateway cross-ref (#11)
            gw_refs = store.find_cross_refs(rp_id, "route_pattern_uses_gateway")
            if gw_refs:
                # Gateway -> trunk mapping
                gw_id = gw_refs[0]
                gw_name = gw_id.split(":", 1)[-1] if ":" in gw_id else gw_id
                target_id = f"trunk:{gw_name}"
                route_type = "TRUNK"
            else:
                # Try route list cross-ref (#12)
                rl_refs = store.find_cross_refs(rp_id, "route_pattern_uses_route_list")
                if rl_refs:
                    # Webex dial plans only support RouteType=ROUTE_GROUP|TRUNK,
                    # so we resolve through the mapped CanonicalRouteList to get
                    # its underlying route_group_id. The route list itself is
                    # created as a parallel standalone resource.
                    rl_id = rl_refs[0]
                    rl_obj = store.get_object(rl_id)
                    if rl_obj and rl_obj.get("route_group_id"):
                        target_id = rl_obj["route_group_id"]
                        route_type = "ROUTE_GROUP"

            # Fall back to pre_migration_state if cross-refs were empty
            if not target_id:
                target_type = state.get("target_type")
                target_name = state.get("target_name")
                if target_name and target_type:
                    if target_type in ("gateway", "trunk"):
                        target_id = f"trunk:{target_name}"
                        route_type = "TRUNK"
                    elif target_type in ("route_list", "routeList", "route_group"):
                        target_id = f"route_group:{target_name}"
                        route_type = "ROUTE_GROUP"

            if not target_id:
                # No target resolved — create MISSING_DATA decision
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary=(
                        f"Route pattern '{cucm_pattern}' has no resolvable routing "
                        f"target — cross-refs and pre_migration_state both empty"
                    ),
                    context={
                        "route_pattern_id": rp_id,
                        "cucm_pattern": cucm_pattern,
                        "reason": "no_routing_target",
                    },
                    options=[
                        manual_option("Admin assigns routing target manually"),
                        skip_option("Pattern not migrated"),
                    ],
                    affected_objects=[rp_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
                skipped_no_target += 1
                continue

            # Accumulate pattern into target group
            target_groups.setdefault(target_id, []).append(webex_pattern)
            if target_id not in target_names:
                target_names[target_id] = target_id.split(":", 1)[-1]
            target_route_types[target_id] = route_type
            rp_count += 1

        logger.info(
            "Dial plan mapping: %d route patterns processed, %d skipped (@ macro), "
            "%d skipped (no target), %d dial plans created",
            rp_count, skipped_at_macro, skipped_no_target, len(target_groups),
        )

        # --- Create CanonicalDialPlan per target ---
        for target_id, patterns in target_groups.items():
            target_name = target_names[target_id]
            route_type = target_route_types[target_id]

            dp_name = f"Migration-DialPlan-{target_name}"

            dial_plan = CanonicalDialPlan(
                canonical_id=f"dial_plan:{hash_id(dp_name)}",
                provenance=Provenance(
                    source_system="cucm",
                    source_id=target_id,
                    source_name=dp_name,
                    extracted_at=datetime.now(timezone.utc),
                ),
                status=MigrationStatus.ANALYZED,
                name=dp_name,
                dial_patterns=sorted(set(patterns)),
                route_id=target_id,
                route_type=route_type,
            )

            store.upsert_object(dial_plan)
            result.objects_created += 1

    # ------------------------------------------------------------------
    # Translation Patterns
    # ------------------------------------------------------------------

    def _map_translation_patterns(
        self, store: MigrationStore, result: MapperResult
    ) -> None:
        """Map CUCM translation patterns to CanonicalTranslationPattern objects.

        (from 03b-transform-mappers.md §6: translation pattern field mapping table)
        """
        tp_objects = list(store.get_objects("translation_pattern"))
        logger.info("Translation pattern mapping: %d source objects found", len(tp_objects))

        for tp_data in tp_objects:
            tp_id = tp_data["canonical_id"]
            state = tp_data.get("pre_migration_state") or {}

            cucm_pattern = state.get("pattern", "")

            # Fix 6: Skip translation patterns with empty/None pattern
            if not cucm_pattern:
                continue
            replacement = state.get("calledPartyTransformationMask", "")
            description = state.get("description") or cucm_pattern

            # --- Convert matching pattern ---
            matching_pattern = cucm_to_webex_pattern(
                cucm_pattern, self.country_code, self.outside_dial_digit
            )

            # --- Validate replacement pattern ---
            # (from 03b-transform-mappers.md §6: "E.164 replacementPattern cannot contain X wildcards")
            replacement_pattern = replacement
            if replacement_pattern and replacement_pattern.startswith("+") and "X" in replacement_pattern.upper():
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary=(
                        f"Translation pattern '{cucm_pattern}' has E.164 replacement "
                        f"'{replacement}' with X wildcards — invalid in Webex"
                    ),
                    context={
                        "translation_pattern_id": tp_id,
                        "cucm_pattern": cucm_pattern,
                        "replacement_pattern": replacement,
                        "reason": "e164_replacement_has_wildcards",
                    },
                    options=[
                        manual_option("Admin provides valid replacement pattern without wildcards"),
                        skip_option("Translation pattern not migrated"),
                    ],
                    affected_objects=[tp_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            tp_obj = CanonicalTranslationPattern(
                canonical_id=f"translation_pattern:{hash_id(cucm_pattern)}",
                provenance=extract_provenance(tp_data),
                status=MigrationStatus.ANALYZED,
                name=description,
                matching_pattern=matching_pattern,
                replacement_pattern=replacement_pattern,
            )

            store.upsert_object(tp_obj)
            result.objects_created += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_trunk_type(state: dict[str, Any]) -> str:
    """Infer Webex trunk type from CUCM SIP trunk settings.

    (from 03b-transform-mappers.md §6: "REGISTERING or CERTIFICATE_BASED")
    Tier 2: Prefer explicit security_mode from profile detail when available.
    """
    # Tier 2: Prefer explicit security_mode from profile detail
    security_mode = (state.get("security_mode") or "").upper()
    if security_mode == "TLS":
        return "CERTIFICATE_BASED"
    if security_mode == "IPSEC":
        return "CERTIFICATE_BASED"  # Closest Webex equivalent
    if security_mode == "NON_SECURE":
        return "REGISTERING"

    # Fallback: pattern-match on security profile name
    security_profile = (state.get("security_profile") or state.get("securityProfileName") or "").lower()
    if "tls" in security_profile or "certificate" in security_profile:
        return "CERTIFICATE_BASED"

    trunk_type = state.get("trunk_type", "").upper()
    if trunk_type == "CERTIFICATE_BASED":
        return "CERTIFICATE_BASED"

    return "REGISTERING"


