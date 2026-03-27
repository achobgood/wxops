"""MOH (Music On Hold) extractor for CUCM AXL.

Pulls MOH Audio Sources from CUCM AXL.

Sources:
- tier2-enterprise-expansion.md §2.3 (MOH extraction)
- AXL WSDL: listMohAudioSource / getMohAudioSource
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# ReturnedTags constants
# ------------------------------------------------------------------

MOH_AUDIO_SOURCE_LIST_RETURNED_TAGS = {
    "name": "",
    "sourceFileName": "",
    "isDefault": "",
    "sourceId": "",
}


class MOHExtractor(BaseExtractor):
    """Extract Music On Hold audio sources from CUCM AXL.

    MOH audio sources define the audio files played to callers on hold.
    CUCM supports multiple audio sources; Webex Calling supports per-location
    MOH with a single audio file or default music.

    (from tier2-enterprise-expansion.md §2.3)
    """

    name = "moh"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        """Run MOH audio source extraction.

        Returns an ExtractionResult summarizing total objects and errors.
        """
        result = ExtractionResult(extractor=self.name)
        self.results["moh_sources"] = self._extract_moh_sources(result)
        return result

    # ------------------------------------------------------------------
    # MOH Audio Sources
    # ------------------------------------------------------------------

    def _extract_moh_sources(
        self, result: ExtractionResult
    ) -> list[dict[str, Any]]:
        """List all MOH audio sources, then get full detail for each.

        Uses listMohAudioSource for summary, getMohAudioSource for detail.
        """
        sources: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(
                "listMohAudioSource",
                {"name": "%"},
                MOH_AUDIO_SOURCE_LIST_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listMohAudioSource failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return sources

        for summary in summaries:
            result.total += 1
            name = summary.get("name", "")
            if not name:
                result.failed += 1
                continue
            try:
                detail = self.get_detail("getMohAudioSource", name=name)
            except Exception as exc:
                logger.warning(
                    "[%s] getMohAudioSource error for %s: %s",
                    self.name, name, exc,
                )
                sources.append(summary)
                continue
            if detail is None:
                sources.append(summary)
                continue
            sources.append({**summary, **detail})

        return sources
