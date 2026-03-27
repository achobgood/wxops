"""Tier 4 feature gap extractor — recording profiles, remote destinations,
transformation patterns, extension mobility device profiles.

Wave 1: extract + flag only. No mappers or execution handlers.
(from docs/prompts/tier4-feature-gap-extraction.md)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

RECORDING_PROFILE_TAGS = {"name": "", "recordingCssName": "", "recorderDestination": ""}
REMOTE_DEST_PROFILE_TAGS = {"name": "", "description": "", "userId": ""}
CALLING_PARTY_XFORM_TAGS = {
    "pattern": "", "description": "", "callingSearchSpaceName": "",
    "routePartitionName": "", "callingPartyTransformationMask": "",
    "callingPartyPrefixDigits": "", "digitDiscardInstructionName": "",
}
CALLED_PARTY_XFORM_TAGS = {
    "pattern": "", "description": "", "callingSearchSpaceName": "",
    "routePartitionName": "", "calledPartyTransformationMask": "",
    "calledPartyPrefixDigits": "", "digitDiscardInstructionName": "",
}
DEVICE_PROFILE_TAGS = {"name": "", "description": "", "product": "", "protocol": ""}


class Tier4Extractor(BaseExtractor):
    """Extract Tier 4 feature gap data from CUCM.

    Extracts:
    - Recording profiles (Item 1)
    - Remote destination profiles / SNR (Item 2)
    - Calling/Called party transformation patterns (Item 4)
    - Extension Mobility device profiles (Item 6)
    """

    name = "tier4"

    def __init__(self, connection: AXLConnection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        result = ExtractionResult(extractor=self.name)
        total = 0
        total += self._extract_type(
            result, "recording_profiles",
            "listRecordingProfile", {"name": "%"}, RECORDING_PROFILE_TAGS,
        )
        total += self._extract_type(
            result, "remote_destination_profiles",
            "listRemoteDestinationProfile", {"name": "%"}, REMOTE_DEST_PROFILE_TAGS,
        )
        total += self._extract_type(
            result, "calling_party_transformations",
            "listCallingPartyTransformationPattern", {"pattern": "%"},
            CALLING_PARTY_XFORM_TAGS,
        )
        total += self._extract_type(
            result, "called_party_transformations",
            "listCalledPartyTransformationPattern", {"pattern": "%"},
            CALLED_PARTY_XFORM_TAGS,
        )
        total += self._extract_type(
            result, "device_profiles",
            "listDeviceProfile", {"name": "%"}, DEVICE_PROFILE_TAGS,
        )
        result.total = total
        return result

    def _extract_type(
        self,
        result: ExtractionResult,
        key: str,
        method: str,
        search_criteria: dict[str, str],
        returned_tags: dict[str, str],
    ) -> int:
        try:
            items = self.paginated_list(method, search_criteria, returned_tags)
        except Exception as exc:
            msg = f"{method} failed: {exc}"
            logger.warning("[%s] %s", self.name, msg)
            result.errors.append(msg)
            self.results[key] = []
            return 0
        self.results[key] = items
        logger.info("[%s] %s: %d objects", self.name, key, len(items))
        return len(items)
