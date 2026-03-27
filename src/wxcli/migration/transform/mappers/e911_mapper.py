"""E911Mapper — CUCM ELIN groups + GeoLocations → E911 advisory.

This mapper is unusual — it doesn't produce Webex-ready objects. CUCM E911
(ELIN-based) and Webex E911 (civic address + RedSky) are architecturally
different systems. The mapper's job is to:
1. Record that E911 was configured in CUCM
2. Produce CanonicalE911Config objects for the report
3. Produce ARCHITECTURE_ADVISORY decisions flagging E911 as a separate workstream

(from tier2-enterprise-expansion.md §6)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalE911Config,
    DecisionType,
    MigrationStatus,
    MapperResult,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    extract_provenance,
    skip_option,
)

logger = logging.getLogger(__name__)


class E911Mapper(Mapper):
    """Map CUCM ELIN groups and geo locations to E911 advisory objects.

    Tier 2 expansion: produces CanonicalE911Config objects and
    ARCHITECTURE_ADVISORY decisions for E911 migration workstream.
    """

    name = "e911_mapper"
    depends_on = ["location_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        elin_groups = store.get_objects("elin_group")
        geo_locations = store.get_objects("geo_location")

        if not elin_groups and not geo_locations:
            return result

        # Check for 911 route patterns in existing data
        has_911_pattern = False
        for rp in store.get_objects("route_pattern"):
            state = rp.get("pre_migration_state") or {}
            pattern = state.get("pattern") or ""
            if pattern in ("911", "9.911", "9911", ".911"):
                has_911_pattern = True
                break

        # Create E911Config objects from ELIN groups
        for elin_data in elin_groups:
            state = elin_data.get("pre_migration_state") or {}
            name = state.get("name") or ""
            elin_numbers = state.get("elin_numbers") or []

            prov = extract_provenance(elin_data)
            config = CanonicalE911Config(
                canonical_id=f"e911_config:{name}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                elin_group_name=name,
                elin_numbers=elin_numbers,
                has_emergency_route_pattern=has_911_pattern,
            )
            store.upsert_object(config)
            result.objects_created += 1

        # Create E911Config objects from geo locations (if no ELIN groups)
        if not elin_groups:
            for geo_data in geo_locations:
                state = geo_data.get("pre_migration_state") or {}
                name = state.get("name") or ""
                country = state.get("country") or ""

                prov = extract_provenance(geo_data)
                config = CanonicalE911Config(
                    canonical_id=f"e911_config:geo:{name}",
                    provenance=prov,
                    status=MigrationStatus.ANALYZED,
                    geo_location_name=name,
                    geo_country=country,
                    has_emergency_route_pattern=has_911_pattern,
                )
                store.upsert_object(config)
                result.objects_created += 1

        # Single ARCHITECTURE_ADVISORY for all E911 data
        total_elins = sum(
            len((e.get("pre_migration_state") or {}).get("elin_numbers", []))
            for e in elin_groups
        )
        decision = self._create_decision(
            store=store,
            decision_type=DecisionType.ARCHITECTURE_ADVISORY,
            severity="HIGH",
            summary=(
                f"E911 configuration detected: {len(elin_groups)} ELIN group(s) "
                f"with {total_elins} number(s), {len(geo_locations)} geo location(s). "
                f"Webex E911 requires separate workstream."
            ),
            context={
                "elin_group_count": len(elin_groups),
                "total_elin_numbers": total_elins,
                "geo_location_count": len(geo_locations),
                "has_911_route_pattern": has_911_pattern,
                "advisory_type": "e911_migration",
            },
            options=[
                accept_option("E911 requires separate workstream — emergency addresses, ECBN, notification config in Webex"),
                skip_option("Acknowledge — mark as out of scope for this migration"),
            ],
            affected_objects=[f"e911_config:{(elin_groups[0].get('pre_migration_state') or {}).get('name', 'unknown')}" if elin_groups else "e911"],
        )
        result.decisions.append(decision)

        return result
