"""Location ambiguity analyzer — finds locations with ambiguous device pool mappings.

Mapper-owned decision type: location_mapper may already produce LOCATION_AMBIGUOUS
decisions. This analyzer backfills any locations the mapper missed or detects
cross-object ambiguities that emerge after the full inventory is mapped.

(from 03-conflict-detection-engine.md, location ambiguity linter)
(from phase-06-analyzers.md, Decision Ownership Table — mapper-owned)
"""

from __future__ import annotations

from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


class LocationAmbiguityAnalyzer(Analyzer):
    """Detects locations with ambiguous CUCM device pool consolidation.

    Sweeps all location objects and flags those whose ``warnings`` list
    contains ambiguity indicators (e.g., multiple device pools consolidated
    with conflicting CUCM location references).

    Skips locations that already have a mapper-produced LOCATION_AMBIGUOUS decision.
    """

    name = "location_ambiguity"
    decision_types = [DecisionType.LOCATION_AMBIGUOUS]
    depends_on: list[str] = []

    # Substrings in warnings that indicate location ambiguity
    _AMBIGUITY_MARKERS = ("ambiguous", "conflicting", "multiple cucm locations", "mismatch")

    def analyze(self, store: MigrationStore) -> list[Decision]:
        decisions: list[Decision] = []

        # Get existing mapper-produced decisions indexed by affected object canonical_id
        existing_ambiguous = self._get_existing_decisions_for_type(
            store, DecisionType.LOCATION_AMBIGUOUS
        )

        locations = store.get_objects("location")

        for location in locations:
            canonical_id = location.get("canonical_id", "")

            # Skip if mapper already produced a LOCATION_AMBIGUOUS decision for this location
            if canonical_id in existing_ambiguous:
                continue

            ambiguity_reasons: list[str] = []

            # Check 1: warnings/errors containing ambiguity markers
            warnings = location.get("warnings", [])
            errors = location.get("errors", [])
            all_messages = warnings + errors

            for msg in all_messages:
                if any(marker in msg.lower() for marker in self._AMBIGUITY_MARKERS):
                    ambiguity_reasons.append(msg)

            # Check 2: multiple consolidated device pools (cross-object signal)
            # A location consolidating 3+ device pools is inherently ambiguous —
            # the mapper may not have flagged it if no CUCM location mismatch
            # was detected, but the admin should still review the consolidation.
            pool_names = location.get("cucm_device_pool_names", [])
            if len(pool_names) >= 3 and not ambiguity_reasons:
                ambiguity_reasons.append(
                    f"Location consolidates {len(pool_names)} device pools: "
                    f"{', '.join(pool_names[:5])}"
                )

            if not ambiguity_reasons:
                continue

            decisions.append(self._build_ambiguous_decision(
                store, location, ambiguity_reasons
            ))

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        pool_names = context.get("cucm_device_pool_names", [])
        return self._hash_fingerprint({
            "canonical_id": context.get("canonical_id", ""),
            "cucm_device_pool_names": sorted(pool_names),
        })

    # ------------------------------------------------------------------
    # Decision builder
    # ------------------------------------------------------------------

    def _build_ambiguous_decision(
        self,
        store: MigrationStore,
        location: dict[str, Any],
        ambiguity_warnings: list[str],
    ) -> Decision:
        canonical_id = location.get("canonical_id", "")
        name = location.get("name", "unknown")
        pool_names = location.get("cucm_device_pool_names", [])

        # Count devices + users depending on this location's device pools
        dependent_count = 0
        for pool_name in pool_names:
            pool_id = f"device_pool:{pool_name}"
            dependent_count += len(store.get_cross_refs(
                to_id=pool_id, relationship="device_in_pool",
            ))
            dependent_count += len(store.get_cross_refs(
                to_id=pool_id, relationship="common_area_device_in_pool",
            ))

        has_address = bool(
            location.get("address", {}).get("address1")
            if isinstance(location.get("address"), dict)
            else None
        )

        context = {
            "canonical_id": canonical_id,
            "location_name": name,
            "cucm_device_pool_names": pool_names,
            "warnings": ambiguity_warnings,
            "dependent_device_count": dependent_count,
            "has_address": has_address,
        }
        options = [
            DecisionOption(
                id="accept",
                label="Accept this location mapping",
                impact=f"Location '{name}' will be created with consolidated device pools: "
                       f"{', '.join(pool_names) or 'none'}",
            ),
            DecisionOption(
                id="provide_address",
                label="Provide address for this location",
                impact=f"Location '{name}' needs a street address to create in Webex. "
                       f"Use 'wxcli cucm decide' to supply address1, city, state, postal_code, country.",
            ),
            DecisionOption(
                id="reassign",
                label="Manually assign to different location",
                impact=f"Device pools {', '.join(pool_names) or 'none'} will be "
                       f"reassigned to a user-specified location",
            ),
            DecisionOption(
                id="split",
                label="Split into separate locations",
                impact=f"Each device pool will become its own Webex location "
                       f"({len(pool_names)} locations)",
            ),
        ]

        # Only offer skip if no devices depend on this location
        if dependent_count == 0:
            options.append(DecisionOption(
                id="skip",
                label="Skip this location (no devices affected)",
                impact=f"Location '{name}' will not be migrated (0 devices in its pools)",
            ))
        else:
            # Make the impact of NOT having an address very clear
            options[1] = DecisionOption(
                id="provide_address",
                label=f"Provide address for this location ({dependent_count} devices depend on it)",
                impact=f"Location '{name}' has {dependent_count} devices in its pools. "
                       f"A street address is REQUIRED to create this location in Webex. "
                       f"Skipping is not available because it would block all {dependent_count} devices.",
            )

        return self._create_decision(
            store=store,
            decision_type=DecisionType.LOCATION_AMBIGUOUS,
            severity="HIGH",
            summary=f"Location '{name}' has ambiguous device pool mapping: "
                    f"{'; '.join(ambiguity_warnings[:2])}",
            context=context,
            options=options,
            affected_objects=[canonical_id],
        )
