"""Device Profile extractor for CUCM AXL.

Pulls Extension Mobility Device Profiles from CUCM.

Sources:
- tier2-enterprise-expansion.md §5 (Extension Mobility extraction)
- AXL WSDL: listDeviceProfile / getDeviceProfile
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import to_list

logger = logging.getLogger(__name__)

DEVICE_PROFILE_LIST_RETURNED_TAGS = {
    "name": "",
    "product": "",
    "protocol": "",
    "class": "",
    "phoneTemplateName": "",
}


class DeviceProfileExtractor(BaseExtractor):
    """Extract Extension Mobility Device Profiles from CUCM AXL.

    Device Profiles are virtual phone configurations that users log into.
    When a user logs into a physical phone, the device profile's lines/settings
    replace the phone's default config.

    (from tier2-enterprise-expansion.md §5)
    """

    name = "device_profiles"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        result = ExtractionResult(extractor=self.name)
        self.results["device_profiles"] = self._extract_device_profiles(result)
        return result

    def _extract_device_profiles(
        self, result: ExtractionResult
    ) -> list[dict[str, Any]]:
        """List all device profiles, then get full detail for each."""
        profiles: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(
                "listDeviceProfile",
                {"name": "%"},
                DEVICE_PROFILE_LIST_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listDeviceProfile failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return profiles

        for summary in summaries:
            result.total += 1
            profile_name = summary.get("name", "")
            if not profile_name:
                result.failed += 1
                continue
            try:
                detail = self.get_detail("getDeviceProfile", name=profile_name)
            except Exception as exc:
                logger.warning(
                    "[%s] getDeviceProfile error for %s: %s",
                    self.name, profile_name, exc,
                )
                profiles.append(summary)
                continue
            if detail is None:
                profiles.append(summary)
                continue

            # Normalize lines
            lines_raw = detail.get("lines") or {}
            detail["lines"] = to_list(lines_raw, "line")

            # Count speed dials and BLF entries
            sd_raw = detail.get("speeddials") or {}
            detail["speeddials"] = to_list(sd_raw, "speeddial")
            blf_raw = detail.get("busyLampFields") or {}
            detail["busyLampFields"] = to_list(blf_raw, "busyLampField")

            profiles.append(detail)

        return profiles
