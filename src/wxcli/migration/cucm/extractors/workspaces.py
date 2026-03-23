"""Workspace (common-area phone) classifier post-processor.

Identifies phones that are common-area devices suitable for Webex Calling
workspace provisioning. Runs as a pass 2 helper against already-extracted
phone data -- does NOT make AXL calls.

Sources:
- 02b-cucm-extraction.md S2.8 (workspace classification)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.extractors.helpers import ref_value

logger = logging.getLogger(__name__)


def is_common_area_device(phone_raw: dict[str, Any]) -> bool:
    """Determine if a phone dict represents a common-area device.

    Classification logic (from 02b S2.8):
    - Must have no ownerUserName (unowned device).
    - Must have device class 'Phone' (excludes CTI ports, route points, etc.).

    Args:
        phone_raw: Raw phone dict from DeviceExtractor.

    Returns:
        True if the phone is a common-area device.
    """
    # ownerUserName may be a reference dict {'_value_1': 'user', 'uuid': '...'}
    # or a plain string. Use ref_value to handle both.
    owner = ref_value(phone_raw.get("ownerUserName"))
    if owner is not None:
        return False

    device_class = phone_raw.get("class", "")
    if device_class not in ("Phone",):
        return False

    return True


class WorkspaceClassifier:
    """Classify common-area phones from DeviceExtractor phone data.

    This is a pass 2 helper, NOT a BaseExtractor subclass. It operates
    entirely on in-memory phone dicts and returns the subset that qualify
    as common-area devices.

    (from 02b S2.8)
    """

    def __init__(self, phones: list[dict]) -> None:
        self.phones = phones

    def classify(self) -> list[dict[str, Any]]:
        """Return the subset of phones that are common-area devices.

        Returns the raw phone dicts unchanged -- transformation is the
        normalizer's job.

        Note: ATA devices (name starts with 'ATA') pass the classification
        since they are technically common-area, but may be incompatible with
        Webex Calling workspaces. Downstream stages should flag these.

        Returns:
            List of raw phone dicts that are common-area devices.
        """
        results = [phone for phone in self.phones if is_common_area_device(phone)]

        ata_count = sum(1 for p in results if p.get("name", "").startswith("ATA"))
        if ata_count:
            logger.warning(
                "Classified %d ATA device(s) as common-area -- these may be "
                "incompatible with Webex Calling workspaces",
                ata_count,
            )

        logger.info(
            "Workspace classification complete: %d of %d phones are common-area",
            len(results),
            len(self.phones),
        )
        return results
