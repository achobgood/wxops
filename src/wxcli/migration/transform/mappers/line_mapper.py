"""Line mapper: CUCM Directory Numbers -> Webex Phone Numbers + Extensions.

Maps CUCM DNs (identified from device line appearances) to CanonicalLine objects
with E.164 normalization. Each unique DN (pattern + partition) becomes one
CanonicalLine.

(from 03b-transform-mappers.md §3, line_mapper)

Cross-ref reads:
    device_has_dn          (Device -> DN) — reverse-queried to find devices per DN
    dn_in_partition        (DN -> Partition)
    device_in_pool         (Device -> DevicePool) — for location chain
    device_pool_to_location (DevicePool -> Location) — for country code

Does NOT produce: EXTENSION_CONFLICT (analyzer-owned)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.models import (
    CanonicalLine,
    DecisionType,
    LineClassification,
    MapperResult,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.e164 import normalize_dn
from wxcli.migration.transform.mappers.base import (
    Mapper,
    decision_to_store_dict,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)

# Webex extension length constraints
# (from 03b-transform-mappers.md §3: "Extensions are 2-10 chars in Webex")
_MIN_EXTENSION_LENGTH = 2
_MAX_EXTENSION_LENGTH = 10


class LineMapper(Mapper):
    """Maps CUCM Directory Numbers to Webex Phone Numbers and Extensions.

    (from 03b-transform-mappers.md §3)
    """

    name = "line_mapper"
    depends_on = ["location_mapper"]

    def __init__(
        self,
        default_country_code: str = "US",
        site_prefix_rules: list[dict] | None = None,
    ) -> None:
        """
        Args:
            default_country_code: ISO 3166-1 alpha-2 code for E.164 normalization
                (from 03b-transform-mappers.md §3: country code from location)
            site_prefix_rules: List of prefix stripping rules from migration config
        """
        self.default_country_code = default_country_code
        self.site_prefix_rules = site_prefix_rules or []

    def map(self, store: MigrationStore) -> MapperResult:
        """Find all unique DNs from device line appearances and produce CanonicalLine objects."""
        result = MapperResult()

        # Collect all unique DN IDs from device_has_dn cross-refs
        all_dn_refs = store.get_cross_refs(relationship="device_has_dn")
        unique_dn_ids: set[str] = set()
        # Track which devices reference each DN (for shared line detection)
        dn_to_devices: dict[str, list[str]] = {}
        for ref in all_dn_refs:
            dn_id = ref["to_id"]
            dev_id = ref["from_id"]
            unique_dn_ids.add(dn_id)
            dn_to_devices.setdefault(dn_id, []).append(dev_id)

        # Build index of pre-computed e164_results from device line appearances
        # (from Phase 04 corrections: CrossReferenceBuilder computes e164_result
        # on each line appearance — the line_mapper can read this directly)
        precomputed_e164: dict[str, dict[str, Any]] = {}
        self._build_precomputed_e164_index(store, dn_to_devices, precomputed_e164)

        for dn_id in sorted(unique_dn_ids):
            # Parse DN ID format: "dn:pattern:partition"
            parts = dn_id.split(":", 2)
            if len(parts) < 2:
                continue
            dn_pattern = parts[1]
            partition = parts[2] if len(parts) > 2 else "<None>"
            country_code: str | None = None

            # Check for pre-computed e164_result from line appearances
            # (from Phase 04 corrections: use e164_result when available)
            cached = precomputed_e164.get(dn_id)
            if cached:
                e164_result_data = cached
                # Build an E164Result-compatible object from the cached dict
                e164_result = _E164ResultProxy(
                    e164=e164_result_data.get("e164"),
                    extension=e164_result_data.get("extension"),
                    raw=dn_pattern,
                    classification=e164_result_data.get("classification", "AMBIGUOUS"),
                )
            else:
                # Fallback: resolve country code and run normalize_dn()
                country_code = self._resolve_country_code(store, dn_id, dn_to_devices)
                e164_result = normalize_dn(
                    dn_pattern, country_code, self.site_prefix_rules
                )

            # Shared line detection
            # (from 03b-transform-mappers.md §3: tag shared:true when multiple devices)
            device_list = dn_to_devices.get(dn_id, [])
            unique_devices = list(set(device_list))
            shared = len(unique_devices) > 1

            # Map classification string to enum
            classification = _classify(e164_result.classification)

            # Build extension and e164 fields
            extension = None
            e164 = None

            if classification == LineClassification.EXTENSION:
                extension = e164_result.extension or dn_pattern
            elif classification in (LineClassification.NATIONAL, LineClassification.E164):
                e164 = e164_result.e164
                # For national/E164 numbers, the raw pattern may also serve as extension
                # if it looks like one. But per the design, extension comes from the
                # classified result — NATIONAL/E164 numbers don't get an extension field
                # unless separately configured. The user_mapper gets bare extension from
                # user_has_primary_dn independently.
                # However: a 10-digit national number IS the extension in many CUCM deployments
                # (from 03b-transform-mappers.md §3: "If classified as EXTENSION: stored as bare extension")
                extension = e164_result.extension
            elif classification == LineClassification.AMBIGUOUS:
                # DN can't be classified
                # (from 03b-transform-mappers.md §3: DN_AMBIGUOUS decision)
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.DN_AMBIGUOUS,
                    severity="MEDIUM",
                    summary=f"DN '{dn_pattern}' (partition: {partition}) cannot be classified as extension, national, or E.164",
                    context={
                        "dn_id": dn_id,
                        "dn_pattern": dn_pattern,
                        "partition": partition,
                        "country_code": country_code,
                    },
                    options=[
                        manual_option("Admin classifies as extension-only"),
                        manual_option("Admin provides correct E.164"),
                        skip_option("Number not migrated"),
                    ],
                    affected_objects=[dn_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
                continue

            # Validate extension length for Webex
            # (from 03b-transform-mappers.md §3: "extensions outside 2-10 chars produce MISSING_DATA")
            if extension and (
                len(extension) < _MIN_EXTENSION_LENGTH
                or len(extension) > _MAX_EXTENSION_LENGTH
            ):
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary=f"DN '{dn_pattern}' resolves to extension '{extension}' which is outside Webex's 2-10 char limit",
                    context={
                        "dn_id": dn_id,
                        "dn_pattern": dn_pattern,
                        "extension": extension,
                        "extension_length": len(extension),
                        "partition": partition,
                    },
                    options=[
                        manual_option("Admin provides valid extension (2-10 chars)"),
                        skip_option("Number not migrated"),
                    ],
                    affected_objects=[dn_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
                # Still create the line object but flag it
                # (user can resolve the decision later)

            line = CanonicalLine(
                canonical_id=f"line:{dn_pattern}:{partition}",
                provenance=Provenance(
                    source_system="cucm",
                    source_id=dn_id,
                    source_name=dn_pattern,
                    extracted_at=datetime.now(timezone.utc),
                ),
                status=MigrationStatus.ANALYZED,
                extension=extension,
                e164=e164,
                classification=classification,
                shared=shared,
                cucm_pattern=dn_pattern,
                route_partition_name=partition if partition != "<None>" else None,
            )

            store.upsert_object(line)
            result.objects_created += 1

        return result

    def _build_precomputed_e164_index(
        self,
        store: MigrationStore,
        dn_to_devices: dict[str, list[str]],
        precomputed: dict[str, dict[str, Any]],
    ) -> None:
        """Build index of pre-computed e164_results from device line appearances.

        After CrossReferenceBuilder runs, each line appearance entry in a device's
        pre_migration_state has e164_result: {e164, extension, classification}.
        We index these by DN ID so the mapper can use them directly.

        (from Phase 04 corrections: line appearances have e164_result already computed)
        """
        seen_devices: set[str] = set()
        for dn_id, device_ids in dn_to_devices.items():
            if dn_id in precomputed:
                continue
            for dev_id in device_ids:
                if dev_id in seen_devices:
                    continue
                seen_devices.add(dev_id)
                # Handle virtual cross-ref IDs gracefully
                # (from Phase 04 corrections: get_object may return None)
                dev_data = store.get_object(dev_id)
                if not dev_data:
                    continue
                state = dev_data.get("pre_migration_state") or {}
                for la in state.get("line_appearances", []):
                    la_dn_id = la.get("dn_canonical_id")
                    e164_res = la.get("e164_result")
                    if la_dn_id and e164_res and la_dn_id not in precomputed:
                        precomputed[la_dn_id] = e164_res

    def _resolve_country_code(
        self,
        store: MigrationStore,
        dn_id: str,
        dn_to_devices: dict[str, list[str]],
    ) -> str:
        """Resolve country code for a DN by following the location chain.

        Chain: DN -> (reverse device_has_dn) -> device -> device_in_pool
               -> device_pool_to_location -> location -> address.country

        (from 03b-transform-mappers.md §3: "country_code comes from the DN's resolved location")

        Handles virtual cross-ref IDs gracefully — if get_object returns None
        for any step, continues to the next device.
        (from Phase 04 corrections: handle get_object returning None)
        """
        device_ids = dn_to_devices.get(dn_id, [])
        for dev_id in device_ids:
            # Follow: device -> device_in_pool -> device_pool_to_location
            location_id = store.resolve_chain(
                dev_id, "device_in_pool", "device_pool_to_location"
            )
            if location_id:
                loc_data = store.get_object(location_id)
                if loc_data:
                    address = loc_data.get("address", {})
                    country = address.get("country")
                    if country:
                        return country
        return self.default_country_code


class _E164ResultProxy:
    """Lightweight proxy matching E164Result interface for pre-computed values.

    Used when e164_result is already available from CrossReferenceBuilder
    rather than calling normalize_dn().
    """

    __slots__ = ("e164", "extension", "raw", "classification")

    def __init__(self, e164: str | None, extension: str | None, raw: str, classification: str):
        self.e164 = e164
        self.extension = extension
        self.raw = raw
        self.classification = classification


def _classify(classification_str: str) -> LineClassification:
    """Convert E164Result classification string to LineClassification enum."""
    try:
        return LineClassification(classification_str)
    except ValueError:
        return LineClassification.AMBIGUOUS
