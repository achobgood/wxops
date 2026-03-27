"""Announcement extractor for CUCM AXL.

Pulls Announcements from CUCM AXL for custom audio migration advisory.

Sources:
- tier2-enterprise-expansion.md §2.4 (announcement extraction)
- AXL WSDL: listAnnouncement / getAnnouncement
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

# returnedTags for listAnnouncement
ANNOUNCEMENT_LIST_RETURNED_TAGS = {
    "name": "",
    "description": "",
}

# Additional fields from getAnnouncement
ANNOUNCEMENT_GET_RETURNED_TAGS = {
    "name": "",
    "description": "",
    "announcementFile": "",
}


class AnnouncementExtractor(BaseExtractor):
    """Extract Announcements from CUCM AXL.

    Announcements are custom audio files uploaded to CUCM and referenced
    by Auto Attendants, Call Queues, MOH sources, and other features.

    (from tier2-enterprise-expansion.md §2.4)
    """

    name = "announcements"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        result = ExtractionResult(extractor=self.name)
        self.results["announcements"] = self._extract_announcements(result)
        return result

    def _extract_announcements(
        self, result: ExtractionResult
    ) -> list[dict[str, Any]]:
        """List all announcements, then get full detail for each."""
        announcements: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(
                "listAnnouncement",
                {"name": "%"},
                ANNOUNCEMENT_LIST_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listAnnouncement failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return announcements

        for summary in summaries:
            result.total += 1
            ann_name = summary.get("name", "")
            if not ann_name:
                result.failed += 1
                continue
            try:
                detail = self.get_detail("getAnnouncement", name=ann_name)
            except Exception as exc:
                logger.warning(
                    "[%s] getAnnouncement error for %s: %s",
                    self.name, ann_name, exc,
                )
                announcements.append(summary)
                continue
            if detail is None:
                announcements.append(summary)
                continue
            # Merge list-level fields into detail
            merged = {**summary, **detail}
            announcements.append(merged)

        return announcements
