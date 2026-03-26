"""Location mapper: CUCM Device Pools -> Webex Calling Locations.

Maps one or more CUCM device pools to a single CanonicalLocation, consolidated
by the CUCM Location entity they reference. Multiple device pools sharing the
same CUCM Location produce exactly one Webex location.

(from 03b-transform-mappers.md §1, location_mapper)

Cross-ref reads:
    device_pool_has_datetime_group (DevicePool -> DateTimeGroup) — timezone
    device_pool_at_cucm_location   (DevicePool -> CUCM Location) — address

Cross-ref writes:
    device_pool_to_location (DevicePool canonical_id -> new location canonical_id)
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.models import (
    CanonicalLocation,
    DecisionType,
    LocationAddress,
    MapperResult,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    decision_to_store_dict,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)

# Max location name length in Webex
# (from 03b-transform-mappers.md §1: "truncate to 80 chars")
_MAX_LOCATION_NAME_LENGTH = 80


class LocationMapper(Mapper):
    """Maps CUCM Device Pools to Webex Calling Locations.

    (from 03b-transform-mappers.md §1)
    """

    name = "location_mapper"
    depends_on: list[str] = []

    def __init__(
        self,
        default_language: str = "en_us",
        default_country: str = "US",
        outside_dial_digit: str = "9",
        site_prefix_rules: list[dict[str, str]] | None = None,
    ) -> None:
        self.default_language = default_language
        self.default_country = default_country
        self.outside_dial_digit = outside_dial_digit
        self.site_prefix_rules = site_prefix_rules or []

    def map(self, store: MigrationStore) -> MapperResult:
        """Read device pools and produce CanonicalLocation objects.

        Consolidation: device pools that share a CUCM Location entity are merged
        into a single CanonicalLocation. The first device pool name is used as the
        location name; all pool names are stored in cucm_device_pool_names.

        (from 03b-transform-mappers.md §1, consolidation edge case)
        """
        result = MapperResult()

        # Phase 1: Group device pools by their CUCM Location reference
        # Key = cucm_location canonical_id, Value = list of device pool dicts
        location_groups: dict[str, list[dict[str, Any]]] = {}
        # Track device pools with no CUCM location reference
        orphan_pools: list[dict[str, Any]] = []

        for dp_data in store.get_objects("device_pool"):
            dp_id = dp_data["canonical_id"]

            # Resolve CUCM Location via cross-ref
            loc_refs = store.find_cross_refs(dp_id, "device_pool_at_cucm_location")
            if loc_refs:
                cucm_loc_id = loc_refs[0]
                location_groups.setdefault(cucm_loc_id, []).append(dp_data)
            else:
                orphan_pools.append(dp_data)

        # Phase 2: Create one CanonicalLocation per CUCM Location group
        for cucm_loc_id, dp_list in location_groups.items():
            location, warnings = self._build_location(store, cucm_loc_id, dp_list)
            for w in warnings:
                location.warnings.append(w)

            store.upsert_object(location)
            result.objects_created += 1

            # Write device_pool_to_location cross-refs for all pools in the group
            for dp_data in dp_list:
                store.add_cross_ref(
                    dp_data["canonical_id"],
                    location.canonical_id,
                    "device_pool_to_location",
                )

        # Phase 3: Handle orphan device pools (no CUCM Location ref)
        for dp_data in orphan_pools:
            dp_id = dp_data["canonical_id"]
            dp_name = dp_data.get("pre_migration_state", {}).get(
                "device_pool_name", dp_id
            )

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.LOCATION_AMBIGUOUS,
                severity="HIGH",
                summary=f"Device pool '{dp_name}' has no CUCM Location reference — cannot determine Webex location",
                context={
                    "device_pool_id": dp_id,
                    "device_pool_name": dp_name,
                },
                options=[
                    manual_option("Admin must provide address and create location manually"),
                    skip_option("Device pool not migrated; users/devices in this pool need reassignment"),
                ],
                affected_objects=[dp_id],
            )
            store.save_decision(decision_to_store_dict(decision))
            result.decisions.append(decision)

        return result

    def _build_location(
        self,
        store: MigrationStore,
        cucm_loc_id: str,
        dp_list: list[dict[str, Any]],
    ) -> tuple[CanonicalLocation, list[str]]:
        """Build a CanonicalLocation from a group of device pools sharing a CUCM Location.

        Returns the location and a list of warning strings.
        """
        warnings: list[str] = []

        # Use first device pool as primary (for naming)
        primary_dp = dp_list[0]
        primary_dp_state = primary_dp.get("pre_migration_state", {})
        dp_names = [
            dp.get("pre_migration_state", {}).get("device_pool_name", dp["canonical_id"])
            for dp in dp_list
        ]

        # Location name from primary device pool, truncated to 80 chars
        # (from 03b-transform-mappers.md §1: "truncate to 80 chars")
        name = dp_names[0]
        if len(name) > _MAX_LOCATION_NAME_LENGTH:
            warnings.append(
                f"Location name truncated from {len(name)} to {_MAX_LOCATION_NAME_LENGTH} chars: '{name}'"
            )
            name = name[:_MAX_LOCATION_NAME_LENGTH]

        # Resolve timezone via device_pool_has_datetime_group cross-ref
        # (from 03b-transform-mappers.md §1: datetime group -> IANA timezone)
        time_zone = None
        dtg_name = None
        dtg_refs = store.find_cross_refs(
            primary_dp["canonical_id"], "device_pool_has_datetime_group"
        )
        if dtg_refs:
            dtg_data = store.get_object(dtg_refs[0])
            if dtg_data:
                dtg_state = dtg_data.get("pre_migration_state", {})
                time_zone = dtg_state.get("timezone")
                dtg_name = dtg_state.get("datetime_group_name")

        # Resolve address from CUCM Location entity
        # The cucm_loc_id is like "cucm_location:SomeName" — may or may not be in the store
        address = LocationAddress(country=self.default_country)
        cucm_loc_data = store.get_object(cucm_loc_id)
        if cucm_loc_data:
            loc_state = cucm_loc_data.get("pre_migration_state", {})
            address = LocationAddress(
                address1=loc_state.get("address1"),
                city=loc_state.get("city"),
                state=loc_state.get("state"),
                postal_code=loc_state.get("postal_code"),
                country=loc_state.get("country") or self.default_country,
            )

        # Canonical ID: single-source if one pool, consolidated hash if multiple
        # (from 03b-transform-mappers.md §13, Canonical ID Convention)
        if len(dp_list) == 1:
            canonical_id = f"location:{primary_dp['canonical_id'].replace('device_pool:', '')}"
        else:
            sorted_ids = sorted(dp["canonical_id"] for dp in dp_list)
            hash_input = "|".join(sorted_ids)
            hash_val = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            canonical_id = f"location:{hash_val}"

        # announcementLanguage must be lowercase
        # (from 03b-transform-mappers.md §1: "Must be lowercase (en_us not en_US)")
        # (from docs/reference/location-call-settings-core.md)
        announcement_language = self.default_language.lower()

        location = CanonicalLocation(
            canonical_id=canonical_id,
            provenance=Provenance(
                source_system="cucm",
                source_id=primary_dp.get("provenance", {}).get("source_id", ""),
                source_name=dp_names[0],
                cluster=primary_dp.get("provenance", {}).get("cluster"),
                extracted_at=datetime.now(timezone.utc),
            ),
            status=MigrationStatus.ANALYZED,
            name=name,
            time_zone=time_zone,
            preferred_language=self.default_language.lower(),
            announcement_language=announcement_language,
            address=address,
            routing_prefix=None,  # Set from config if available
            outside_dial_digit=str(self.outside_dial_digit) if self.outside_dial_digit is not None else None,
            calling_enabled=True,
            cucm_device_pool_names=dp_names,
            cucm_datetime_group_name=dtg_name,
            cucm_location_name=cucm_loc_id.replace("cucm_location:", ""),
        )

        return location, warnings
