"""DECT mapper: Canonical DECT networks -> enriched Webex DECT Network objects.

Reads CanonicalDECTNetwork objects produced by normalize_dect_group() (post-normalization
step), resolves locations via device_pool_to_location cross-refs, resolves handset owners
via device_owned_by_user cross-refs, merges any operator-provided base station inventory,
auto-selects network model (DBS-110 vs DBS-210), and generates decisions for ambiguous cases.

(from docs/superpowers/specs/2026-04-10-dect-migration.md §5c, §7a, §7b)

Cross-ref reads:
    device_pool_to_location  (DevicePool -> Location)      — resolve location per network
    device_owned_by_user     (Device -> EndUser)           — resolve handset owner

Decisions generated:
    DECT_NETWORK_DESIGN      — missing location, no base station inventory, or
                               multiple zones map to same location
    DECT_HANDSET_ASSIGNMENT  — handset has no owner (unowned/shared handset)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalDECTNetwork,
    DecisionType,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    decision_to_store_dict,
    extract_provenance,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)

# Handset count threshold: zones with > 30 handsets require DBS-210.
# Zones with <= 30 handsets default to DBS-110.
# (from spec §3c: DBS-110 max 30 line ports; DBS-210 max 1000 line ports)
_DBS110_MAX_HANDSETS = 30


class DECTMapper(Mapper):
    """Map normalized DECT networks to enriched Webex DECT Network objects.

    Runs after location_mapper (so device_pool_to_location cross-refs are set),
    device_mapper (so DECT-tier devices exist in the store), and user_mapper
    (so device_owned_by_user cross-refs can be resolved to canonical user IDs).

    (from docs/superpowers/specs/2026-04-10-dect-migration.md §5c)
    """

    name = "dect_mapper"
    depends_on = ["location_mapper", "device_mapper", "user_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        """Read CanonicalDECTNetwork objects and enrich them with resolved data."""
        result = MapperResult()

        networks = store.get_objects("dect_network")
        if not networks:
            return result

        # Build a map of location_canonical_id -> list of network canonical_ids
        # to detect when multiple zones share the same location.
        # (spec §7a: "multiple device pools with DECT handsets map to the same Webex location")
        location_to_networks: dict[str, list[str]] = {}

        for network_data in networks:
            network_cid = network_data["canonical_id"]
            pool_name = (network_data.get("pre_migration_state") or {}).get("cucm_device_pool", "")

            # --- Location resolution ---
            # device_pool_to_location cross-ref is written by LocationMapper.
            # The network's pre_migration_state.cucm_device_pool is the device pool name.
            pool_id = f"device_pool:{pool_name}" if pool_name else None
            location_canonical_id: str | None = None

            if pool_id:
                loc_refs = store.find_cross_refs(pool_id, "device_pool_to_location")
                location_canonical_id = loc_refs[0] if loc_refs else None

            if location_canonical_id:
                location_to_networks.setdefault(location_canonical_id, []).append(network_cid)

            # Store location on the network for the second pass below
            # (we update the network objects after the full scan)
            network_data["_resolved_location"] = location_canonical_id

        # Second pass: update each network with resolved data and generate decisions.
        for network_data in networks:
            network_cid = network_data["canonical_id"]
            pool_name = (network_data.get("pre_migration_state") or {}).get("cucm_device_pool", "")
            location_canonical_id = network_data.pop("_resolved_location", None)

            handset_assignments: list[dict[str, Any]] = network_data.get("handset_assignments", [])
            handset_count = len(handset_assignments)

            # --- Auto-select network model ---
            # DBS-110 supports up to 30 handsets / 1 base station.
            # DBS-210 supports up to 1000 handsets / 254 base stations.
            # (spec §5c rule 5)
            model = "DBS-110" if handset_count <= _DBS110_MAX_HANDSETS else "DBS-210"

            # --- Resolve handset owners and detect unowned handsets ---
            enriched_assignments: list[dict[str, Any]] = []
            for assignment in handset_assignments:
                device_cid = assignment.get("device_canonical_id")
                owner_canonical_id: str | None = None

                if device_cid:
                    # device_owned_by_user cross-ref source is the device canonical_id
                    owner_refs = store.find_cross_refs(device_cid, "device_owned_by_user")
                    owner_canonical_id = owner_refs[0] if owner_refs else None

                enriched = dict(assignment)
                enriched["user_canonical_id"] = owner_canonical_id
                enriched_assignments.append(enriched)

                # Generate DECT_HANDSET_ASSIGNMENT for unowned handsets
                if owner_canonical_id is None:
                    cucm_device_name = assignment.get("cucm_device_name", device_cid or "unknown")
                    decision = self._create_decision(
                        store=store,
                        decision_type=DecisionType.DECT_HANDSET_ASSIGNMENT,
                        severity="INFO",
                        summary=(
                            f"DECT handset '{cucm_device_name}' has no owner — "
                            f"needs person or workspace assignment"
                        ),
                        context={
                            "device_canonical_id": device_cid,
                            "cucm_device_name": cucm_device_name,
                            "device_pool": pool_name,
                            "owner_status": "unowned",
                            "network_canonical_id": network_cid,
                        },
                        options=[
                            accept_option(
                                "Create a Webex workspace for this handset and assign as PLACE"
                            ),
                            manual_option(
                                "Assign to a specific person (operator provides person ID/email)"
                            ),
                            skip_option("Do not migrate this handset"),
                        ],
                        affected_objects=[network_cid],
                    )
                    store.save_decision(decision_to_store_dict(decision))
                    result.decisions.append(decision)

            # --- Merge operator-provided base station inventory ---
            # Base station data lives in pre_migration_state.base_stations if provided
            # via --dect-inventory flag on discover. If absent, base_stations stays empty.
            base_stations: list[dict[str, Any]] = (
                (network_data.get("pre_migration_state") or {}).get("base_stations", [])
                or network_data.get("base_stations", [])
            )
            has_inventory = bool(base_stations)

            # --- Generate DECT_NETWORK_DESIGN decisions for ambiguous cases ---

            # Case 1: No location resolved
            if location_canonical_id is None:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.DECT_NETWORK_DESIGN,
                    severity="HIGH",
                    summary=(
                        f"DECT network for pool '{pool_name}' could not resolve a "
                        f"target Webex location — manual assignment required"
                    ),
                    context={
                        "network_canonical_id": network_cid,
                        "cucm_device_pool": pool_name,
                        "total_handsets": handset_count,
                        "base_stations_provided": has_inventory,
                        "location_name": None,
                        "zone_count": 1,
                        "handsets_per_zone": {pool_name: handset_count},
                    },
                    options=[
                        manual_option(
                            "Assign this DECT network to a Webex location and re-run the mapper"
                        ),
                        skip_option("Exclude this DECT network from migration"),
                    ],
                    affected_objects=[network_cid],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            # Case 2: No base station inventory provided
            if not has_inventory:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.DECT_NETWORK_DESIGN,
                    severity="MEDIUM",
                    summary=(
                        f"DECT network for pool '{pool_name}' has no base station inventory — "
                        f"provide MAC addresses to enable automated provisioning"
                    ),
                    context={
                        "network_canonical_id": network_cid,
                        "cucm_device_pool": pool_name,
                        "total_handsets": handset_count,
                        "base_stations_provided": False,
                        "location_name": location_canonical_id,
                        "zone_count": 1,
                        "handsets_per_zone": {pool_name: handset_count},
                    },
                    options=[
                        accept_option(
                            f"Create one {'DBS-210' if handset_count > _DBS110_MAX_HANDSETS else 'DBS-110'} "
                            f"DECT network for this zone — base stations must be added manually in Control Hub"
                        ),
                        manual_option(
                            "Provide base station inventory CSV (--dect-inventory) and re-run"
                        ),
                        skip_option("Operator will design DECT networks manually in Control Hub"),
                    ],
                    affected_objects=[network_cid],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            # Case 3: Multiple zones map to the same location (detected via location_to_networks)
            if location_canonical_id and len(location_to_networks.get(location_canonical_id, [])) > 1:
                # Only emit this decision for the first network in the location group to avoid
                # N duplicate decisions. The first network is the canonical_id at index 0.
                zone_group = location_to_networks[location_canonical_id]
                if zone_group[0] == network_cid:
                    # Collect per-zone handset counts for all networks in this location
                    handsets_per_zone: dict[str, int] = {}
                    total_in_loc = 0
                    for sibling_cid in zone_group:
                        sibling_data = next(
                            (n for n in networks if n["canonical_id"] == sibling_cid), {}
                        )
                        sibling_pool = (sibling_data.get("pre_migration_state") or {}).get(
                            "cucm_device_pool", sibling_cid
                        )
                        sibling_count = len(sibling_data.get("handset_assignments", []))
                        handsets_per_zone[sibling_pool] = sibling_count
                        total_in_loc += sibling_count

                    decision = self._create_decision(
                        store=store,
                        decision_type=DecisionType.DECT_NETWORK_DESIGN,
                        severity="MEDIUM",
                        summary=(
                            f"Multiple DECT coverage zones ({len(zone_group)}) map to the same "
                            f"Webex location '{location_canonical_id}' — "
                            f"decide: one combined network or separate networks per zone"
                        ),
                        context={
                            "network_canonical_id": network_cid,
                            "location_name": location_canonical_id,
                            "zone_count": len(zone_group),
                            "total_handsets": total_in_loc,
                            "handsets_per_zone": handsets_per_zone,
                            "base_stations_provided": has_inventory,
                        },
                        options=[
                            accept_option(
                                "Create one DBS-210 multi-cell network for the location — "
                                "all base stations and handsets go into this network"
                            ),
                            manual_option(
                                "Create separate DECT networks per coverage zone — "
                                "provide zone-to-base-station mapping"
                            ),
                            skip_option(
                                "Operator will design DECT networks manually in Control Hub "
                                "after migration"
                            ),
                        ],
                        affected_objects=zone_group,
                    )
                    store.save_decision(decision_to_store_dict(decision))
                    result.decisions.append(decision)

            # --- Build and upsert the enriched CanonicalDECTNetwork ---
            provenance = extract_provenance(network_data)
            enriched_network = CanonicalDECTNetwork(
                canonical_id=network_cid,
                provenance=provenance,
                status=MigrationStatus.ANALYZED,
                location_canonical_id=location_canonical_id,
                network_name=network_data.get("network_name") or f"DECT-{pool_name}",
                display_name=network_data.get("display_name"),
                model=model,
                access_code=network_data.get("access_code") or "",
                base_stations=base_stations,
                handset_assignments=enriched_assignments,
                pre_migration_state={
                    **(network_data.get("pre_migration_state") or {}),
                    "handset_count": handset_count,
                    "has_base_station_inventory": has_inventory,
                    "auto_selected_model": model,
                },
            )

            store.upsert_object(enriched_network)
            result.objects_created += 1

        return result
