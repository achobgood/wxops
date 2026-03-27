"""Device extractor — phones with line appearances.

Two-step extraction: listPhone discovers devices, then getPhone fetches
full detail including nested line/speed-dial data per device.

Sources:
- 02b-cucm-extraction.md §2.3 (device extraction, line appearances)
- 02b-cucm-extraction.md §3 (base extractor, pagination)
"""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import ref_value, to_list

logger = logging.getLogger(__name__)
console = Console()

# Step 1: listPhone — lightweight discovery
PHONE_LIST_RETURNED_TAGS = {
    'name': '', 'model': '', 'ownerUserName': '', 'devicePoolName': '',
    'protocol': '', 'description': '',
}

# Step 2: getPhone — full detail per device
PHONE_GET_RETURNED_TAGS = {
    'name': '', 'model': '', 'description': '', 'ownerUserName': '',
    'devicePoolName': '', 'protocol': '', 'callingSearchSpaceName': '',
    'phoneTemplateName': '', 'softkeyTemplateName': '', 'deviceMobilityMode': '',
    'product': '', 'class': '', 'lines': '',
    'speeddials': '', 'busyLampFields': '',
}


class DeviceExtractor(BaseExtractor):
    """Extract phones and their line appearances from CUCM.

    (from 02b §2.3)
    """

    name = "devices"

    def __init__(self, connection: AXLConnection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        """Run two-step phone extraction.

        Step 1: listPhone with pagination to discover all devices.
        Step 2: getPhone per device for full line appearance data.
        """
        result = ExtractionResult(extractor=self.name)

        # Step 1: discover all phones
        logger.info("[%s] Listing phones...", self.name)
        try:
            phone_summaries = self.paginated_list(
                method_name="listPhone",
                search_criteria={"name": "%"},
                returned_tags=PHONE_LIST_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listPhone failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            self.results["phones"] = []
            return result
        logger.info("[%s] Found %d phones", self.name, len(phone_summaries))
        result.total = len(phone_summaries)

        # Step 2: get full detail per phone
        phones: list[dict[str, Any]] = []
        total = len(phone_summaries)
        for i, summary in enumerate(phone_summaries, 1):
            if i % 200 == 0:
                console.print(f"    phones: {i}/{total}...")
            phone_name = ref_value(summary.get("name")) or summary.get("name")
            if not phone_name:
                result.failed += 1
                result.errors.append("Phone with no name in listPhone result")
                continue

            detail = self._get_phone_detail(phone_name)
            if detail is None:
                result.failed += 1
                result.errors.append(f"getPhone failed for {phone_name}")
                continue

            phones.append(detail)

        self.results["phones"] = phones
        logger.info(
            "[%s] Extracted %d/%d phones (%d failed)",
            self.name, result.success_count, result.total, result.failed,
        )
        return result

    def _get_phone_detail(self, phone_name: str) -> dict[str, Any] | None:
        """Fetch full phone detail and normalize line appearances.

        Handles edge cases:
        - lines may be empty dict or None
        - lines.line may be a single dict, not a list
        - Speed dials are interleaved with lines — filter to entries with ``dirn``
        """
        try:
            detail = self.get_detail("getPhone", name=phone_name)
        except Exception as exc:
            logger.warning("[%s] getPhone error for %s: %s", self.name, phone_name, exc)
            return None

        if detail is None:
            return None

        # Normalize lines — may be None, empty dict, or populated
        raw_lines = detail.get("lines")
        line_entries = to_list(raw_lines, "line")

        # Filter: only entries with a ``dirn`` key are real line appearances.
        # Speed dial entries are interleaved but lack ``dirn``.
        line_appearances = []
        for entry in line_entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("dirn") is not None:
                line_appearances.append(entry)

        detail["lines"] = line_appearances

        # Enrich each line with call forwarding settings from getLine.
        # getPhone line entries do NOT include callForwardAll/Busy/NoAnswer —
        # those are only on the Line AXL object. The voicemail_mapper needs
        # these to determine sendAllCalls/sendBusyCalls/sendUnansweredCalls.
        # Verified against live CUCM 15.0 (2026-03-23): getLine response
        # includes callForwardAll, callForwardBusy, callForwardNoAnswer with
        # forwardToVoiceMail, destination, and duration fields.
        for line_entry in line_appearances:
            dirn = line_entry.get("dirn")
            if not isinstance(dirn, dict):
                continue
            pattern = dirn.get("pattern")
            partition = ref_value(dirn.get("routePartitionName"))
            if not pattern:
                continue
            self._enrich_line_with_forwarding(line_entry, pattern, partition)

        return detail

    def _enrich_line_with_forwarding(
        self, line_entry: dict[str, Any], pattern: str, partition: str | None,
    ) -> None:
        """Fetch getLine for a DN and merge call forwarding settings into the line entry."""
        try:
            kwargs: dict[str, Any] = {"pattern": pattern}
            if partition:
                kwargs["routePartitionName"] = partition
            line_detail = self.get_detail("getLine", **kwargs)
        except Exception as exc:
            logger.debug(
                "[%s] getLine(%s/%s) failed: %s", self.name, pattern, partition, exc,
            )
            return
        if line_detail is None:
            return
        # Merge forwarding fields into the line entry
        for fwd_key in (
            "callForwardAll", "callForwardBusy", "callForwardBusyInt",
            "callForwardNoAnswer", "callForwardNoAnswerInt",
            "callForwardNoCoverage", "callForwardNoCoverageInt",
            "callForwardNotRegistered", "callForwardNotRegisteredInt",
            "callForwardOnFailure",
        ):
            if fwd_key in line_detail:
                line_entry[fwd_key] = line_detail[fwd_key]
        # Also grab voiceMailProfileName if present on the Line
        if "voiceMailProfileName" in line_detail:
            line_entry["voiceMailProfileName"] = line_detail["voiceMailProfileName"]
        # Grab recording fields if present on the Line
        if "recordingProfileName" in line_detail:
            line_entry["recordingProfileName"] = line_detail["recordingProfileName"]
        if "recordingFlag" in line_detail:
            line_entry["recordingFlag"] = line_detail["recordingFlag"]
