"""Locations extractor — Device Pools, DateTime Groups, CUCM Locations.

Extracts CUCM location-related entities that feed the location_mapper
(from 03b §1), which maps Device Pools → Webex Calling Locations.

Sources:
- 02b-cucm-extraction.md §2.1 (locations extractor spec)
- 03b-transform-mappers.md §1 (location_mapper field mapping)
- 02-normalization-architecture.md cross-ref #1, #2
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import ref_value, to_list

logger = logging.getLogger(__name__)

# --- returnedTags constants (from 02b §2.1) ---

DEVICE_POOL_RETURNED_TAGS = {
    'name': '',                          # The device pool name itself (maps to location name)
    'dateTimeSettingName': '',           # Reference → DateTime Group (cross-ref #1)
    'locationName': '',                  # Reference → CUCM Location entity (cross-ref #2)
    'callManagerGroupName': '',          # Not migratable — "Webex is cloud-managed"
    'srstName': '',                      # Not migratable — "on-prem only"
    'regionName': '',                    # Not migratable — "cloud-managed"
    'mediaResourceListName': '',         # Not migratable — "cloud-managed"
}

DATETIME_GROUP_RETURNED_TAGS = {
    'name': '',                          # DateTime group name (referenced by device pool)
    'timeZone': '',                      # IANA timezone string — verified via pipeline execution
}

CUCM_LOCATION_RETURNED_TAGS = {
    'name': '',                          # Location entity name
    # Address fields not present on CAC Location object — verified via pipeline execution
}


class LocationExtractor(BaseExtractor):
    """Extract Device Pools, DateTime Groups, and CUCM Locations.

    Three-entity extractor:
    1. Device Pools — discovered via listDevicePool, full detail via getDevicePool
    2. DateTime Groups — discovered via listDateTimeGroup, detail via getDateTimeGroup
    3. CUCM Locations — discovered via listLocation (verified via pipeline execution)

    Results stored in self.results with keys:
        device_pools, datetime_groups, cucm_locations

    (from 02b §2.1)
    """

    name = "locations"

    def __init__(self, connection: AXLConnection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {
            'device_pools': [],
            'datetime_groups': [],
            'cucm_locations': [],
        }

    def extract(self) -> ExtractionResult:
        """Run all three sub-extractions and return combined result."""
        total = 0
        failed = 0
        errors: list[str] = []

        # --- Device Pools ---
        dp_total, dp_failed, dp_errors = self._extract_device_pools()
        total += dp_total
        failed += dp_failed
        errors.extend(dp_errors)

        # --- DateTime Groups ---
        dt_total, dt_failed, dt_errors = self._extract_datetime_groups()
        total += dt_total
        failed += dt_failed
        errors.extend(dt_errors)

        # --- CUCM Locations ---
        loc_total, loc_failed, loc_errors = self._extract_cucm_locations()
        total += loc_total
        failed += loc_failed
        errors.extend(loc_errors)

        return ExtractionResult(
            extractor=self.name,
            total=total,
            failed=failed,
            errors=errors,
        )

    def _extract_device_pools(self) -> tuple[int, int, list[str]]:
        """List all device pools, then get full detail for each.

        listDevicePool returns summary; getDevicePool returns full references
        (datetime group, CUCM location, region, SRST).
        (from 02b §2.1 AXL Method Mapping)
        """
        errors: list[str] = []
        failed = 0

        try:
            summary_list = self.paginated_list(
                'listDevicePool',
                search_criteria={'name': '%'},
                returned_tags=DEVICE_POOL_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listDevicePool failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            return 0, 0, [msg]
        total = len(summary_list)
        logger.info("Found %d device pools via listDevicePool", total)

        for dp_summary in summary_list:
            dp_name = dp_summary.get('name', '<unknown>')
            try:
                detail = self.get_detail('getDevicePool', name=dp_name)
                if detail is not None:
                    self.results['device_pools'].append(detail)
                else:
                    logger.warning("getDevicePool returned None for '%s'", dp_name)
                    failed += 1
                    errors.append(f"getDevicePool returned None for '{dp_name}'")
            except Exception as exc:
                logger.warning("getDevicePool failed for '%s': %s", dp_name, exc)
                failed += 1
                errors.append(f"getDevicePool failed for '{dp_name}': {exc}")

        logger.info(
            "Device pools: %d total, %d succeeded, %d failed",
            total, total - failed, failed,
        )
        return total, failed, errors

    def _extract_datetime_groups(self) -> tuple[int, int, list[str]]:
        """List all DateTime Groups, then get full detail for each.

        Get returns timezone name and offset details.
        (from 02b §2.1 AXL Method Mapping)
        """
        errors: list[str] = []
        failed = 0

        try:
            summary_list = self.paginated_list(
                'listDateTimeGroup',
                search_criteria={'name': '%'},
                returned_tags=DATETIME_GROUP_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listDateTimeGroup failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            return 0, 0, [msg]
        total = len(summary_list)
        logger.info("Found %d datetime groups via listDateTimeGroup", total)

        for dtg_summary in summary_list:
            dtg_name = dtg_summary.get('name', '<unknown>')
            try:
                detail = self.get_detail('getDateTimeGroup', name=dtg_name)
                if detail is not None:
                    self.results['datetime_groups'].append(detail)
                else:
                    logger.warning("getDateTimeGroup returned None for '%s'", dtg_name)
                    failed += 1
                    errors.append(f"getDateTimeGroup returned None for '{dtg_name}'")
            except Exception as exc:
                logger.warning("getDateTimeGroup failed for '%s': %s", dtg_name, exc)
                failed += 1
                errors.append(f"getDateTimeGroup failed for '{dtg_name}': {exc}")

        logger.info(
            "DateTime groups: %d total, %d succeeded, %d failed",
            total, total - failed, failed,
        )
        return total, failed, errors

    def _extract_cucm_locations(self) -> tuple[int, int, list[str]]:
        """List all CUCM Location entities.

        CUCM Locations are primarily for Call Admission Control (bandwidth).
        May not contain physical address fields.
        Verified via pipeline execution against CUCM 15.0 testbed.
        (from 02b §2.1 design decision)
        """
        errors: list[str] = []
        failed = 0

        try:
            summary_list = self.paginated_list(
                'listLocation',
                search_criteria={'name': '%'},
                returned_tags=CUCM_LOCATION_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listLocation failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            return 0, 0, [msg]
        total = len(summary_list)
        logger.info("Found %d CUCM locations via listLocation", total)

        # CUCM Location entities are simple enough that list may return
        # all needed fields. Store directly without per-object get.
        for loc in summary_list:
            self.results['cucm_locations'].append(loc)

        logger.info(
            "CUCM locations: %d total, %d succeeded, %d failed",
            total, total - failed, failed,
        )
        return total, failed, errors
