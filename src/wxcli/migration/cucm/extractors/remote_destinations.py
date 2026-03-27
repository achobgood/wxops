"""Remote Destination extractor for CUCM AXL.

Pulls Remote Destinations (mobile numbers for Single Number Reach) from CUCM.

Sources:
- tier2-enterprise-expansion.md §4 (SNR extraction)
- AXL WSDL: listRemoteDestination / getRemoteDestination
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

# returnedTags for listRemoteDestination (from tier2 spec §4)
REMOTE_DEST_LIST_RETURNED_TAGS = {
    "name": "",
    "destination": "",
    "ownerUserId": "",
    "isMobilePhone": "",
    "enableMobileConnect": "",
}

# Additional fields from getRemoteDestination
REMOTE_DEST_GET_RETURNED_TAGS = {
    "answerTooSoonTimer": "",
    "answerTooLateTimer": "",
    "lineAssociations": "",
    "remoteDestinationProfileName": "",
}


class RemoteDestinationExtractor(BaseExtractor):
    """Extract Remote Destinations from CUCM AXL.

    Remote Destinations define mobile numbers that ring when a user's
    desk phone rings (Single Number Reach / Mobile Connect).

    (from tier2-enterprise-expansion.md §4)
    """

    name = "remote_destinations"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        result = ExtractionResult(extractor=self.name)
        self.results["remote_destinations"] = self._extract_remote_destinations(result)
        return result

    def _extract_remote_destinations(
        self, result: ExtractionResult
    ) -> list[dict[str, Any]]:
        """List all remote destinations, then get full detail for each."""
        destinations: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(
                "listRemoteDestination",
                {"name": "%"},
                REMOTE_DEST_LIST_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listRemoteDestination failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return destinations

        for summary in summaries:
            result.total += 1
            dest_name = summary.get("name", "")
            if not dest_name:
                result.failed += 1
                continue
            try:
                detail = self.get_detail("getRemoteDestination", name=dest_name)
            except Exception as exc:
                logger.warning(
                    "[%s] getRemoteDestination error for %s: %s",
                    self.name, dest_name, exc,
                )
                destinations.append(summary)
                continue
            if detail is None:
                destinations.append(summary)
                continue
            # Merge list-level fields into detail (detail may not have all list fields)
            merged = {**summary, **detail}
            destinations.append(merged)

        return destinations
