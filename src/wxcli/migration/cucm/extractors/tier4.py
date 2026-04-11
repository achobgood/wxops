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
_BLOCKED_PARTITION_SQL = """\
SELECT n.dnorpattern, rp.name as partition_name, eu.userid
FROM numplan n
JOIN routepartition rp ON rp.pkid = n.fkroutepartition
LEFT JOIN devicenumplanmap dnpm ON dnpm.fknumplan = n.pkid
LEFT JOIN device d ON d.pkid = dnpm.fkdevice
LEFT JOIN enduser eu ON eu.pkid = d.fkenduser
WHERE LOWER(rp.name) LIKE '%intercept%'
   OR LOWER(rp.name) LIKE '%block%'
   OR LOWER(rp.name) LIKE '%out_of_service%'
   OR LOWER(rp.name) LIKE '%oos%'
"""

_CFA_VOICEMAIL_SQL = """\
SELECT n.dnorpattern, rp.name as partition_name,
       cfwd.cfadestination, eu.userid
FROM numplan n
LEFT JOIN routepartition rp ON rp.pkid = n.fkroutepartition
JOIN callforwarddynamic cfwd ON cfwd.fknumplan = n.pkid
LEFT JOIN devicenumplanmap dnpm ON dnpm.fknumplan = n.pkid
LEFT JOIN device d ON d.pkid = dnpm.fkdevice
LEFT JOIN enduser eu ON eu.pkid = d.fkenduser
WHERE cfwd.cfadestination IS NOT NULL
  AND cfwd.cfadestination != ''
  AND cfwd.cfavoicemailenabled = 't'
  AND NOT EXISTS (
      SELECT 1 FROM device d2
      JOIN devicenumplanmap dnpm2 ON dnpm2.fkdevice = d2.pkid
      WHERE dnpm2.fknumplan = n.pkid
        AND d2.tkclass = 1
        AND d2.tkstatus_registrationstate = 2
  )
"""


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
        total += self._extract_intercept_candidates(result)
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

    def _extract_intercept_candidates(self, result: ExtractionResult) -> int:
        """Detect intercept-like configurations via SQL heuristics."""
        seen: dict[str, dict[str, Any]] = {}
        try:
            rows = self.conn.execute_sql(_BLOCKED_PARTITION_SQL)
            for row in rows:
                dn = row.get("dnorpattern", "")
                if not dn:
                    continue
                seen[dn] = {
                    "userid": row.get("userid") or "",
                    "dn": dn,
                    "partition": row.get("partition_name") or "",
                    "signal_type": "blocked_partition",
                    "forward_destination": "",
                    "voicemail_enabled": False,
                }
        except Exception as exc:
            msg = f"Intercept blocked-partition SQL failed: {exc}"
            logger.warning("[%s] %s", self.name, msg)
            result.errors.append(msg)
        try:
            rows = self.conn.execute_sql(_CFA_VOICEMAIL_SQL)
            for row in rows:
                dn = row.get("dnorpattern", "")
                if not dn or dn in seen:
                    continue
                seen[dn] = {
                    "userid": row.get("userid") or "",
                    "dn": dn,
                    "partition": row.get("partition_name") or "",
                    "signal_type": "cfa_voicemail",
                    "forward_destination": row.get("cfadestination") or "",
                    "voicemail_enabled": True,
                }
        except Exception as exc:
            msg = f"Intercept CFA-voicemail SQL failed: {exc}"
            logger.warning("[%s] %s", self.name, msg)
            result.errors.append(msg)
        candidates = list(seen.values())
        self.results["intercept_candidates"] = candidates
        logger.info("[%s] intercept_candidates: %d objects", self.name, len(candidates))
        return len(candidates)
