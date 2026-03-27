"""E911 extractor for CUCM AXL.

Pulls ELIN groups and geographic locations from CUCM for E911 advisory.

Sources:
- tier2-enterprise-expansion.md §6 (E911/ELIN extraction)
- AXL WSDL: listElinGroup / getElinGroup, listGeoLocation / getGeoLocation
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

ELIN_GROUP_LIST_RETURNED_TAGS = {
    "name": "",
    "elinNumbers": "",
}

GEO_LOCATION_LIST_RETURNED_TAGS = {
    "name": "",
    "description": "",
    "country": "",
}


class E911Extractor(BaseExtractor):
    """Extract E911 ELIN groups and geographic locations from CUCM AXL.

    ELIN groups define E.164 numbers reserved for E911 callback.
    Geographic locations define E911 routing by country/region.
    CER (Cisco Emergency Responder) is out of scope — it has its own DB.

    (from tier2-enterprise-expansion.md §6)
    """

    name = "e911"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        result = ExtractionResult(extractor=self.name)
        self.results["elin_groups"] = self._extract_elin_groups(result)
        self.results["geo_locations"] = self._extract_geo_locations(result)
        return result

    def _extract_elin_groups(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """List all ELIN groups."""
        groups: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(
                "listElinGroup",
                {"name": "%"},
                ELIN_GROUP_LIST_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listElinGroup failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return groups

        for summary in summaries:
            result.total += 1
            name = summary.get("name", "")
            if not name:
                result.failed += 1
                continue
            try:
                detail = self.get_detail("getElinGroup", name=name)
            except Exception as exc:
                logger.warning("[%s] getElinGroup error for %s: %s", self.name, name, exc)
                groups.append(summary)
                continue
            if detail is None:
                groups.append(summary)
                continue
            groups.append({**summary, **detail})

        return groups

    def _extract_geo_locations(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """List all geographic locations."""
        locations: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(
                "listGeoLocation",
                {"name": "%"},
                GEO_LOCATION_LIST_RETURNED_TAGS,
            )
            locations.extend(summaries)
            result.total += len(summaries)
        except Exception as exc:
            msg = f"listGeoLocation failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)

        return locations
