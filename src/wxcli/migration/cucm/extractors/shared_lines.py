"""Shared line detection post-processor.

Identifies directory numbers that appear on two or more devices, indicating
shared-line appearances. Runs as a pass 2 helper against already-extracted
phone data -- does NOT make AXL calls.

Sources:
- 02b-cucm-extraction.md S2.7 (shared line detection)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from wxcli.migration.cucm.extractors.helpers import ref_value, to_list

logger = logging.getLogger(__name__)


class SharedLineDetector:
    """Detect shared lines from DeviceExtractor phone data.

    This is a pass 2 helper, NOT a BaseExtractor subclass. It operates
    entirely on in-memory phone dicts and produces shared line records.

    (from 02b S2.7)
    """

    def __init__(self, phones: list[dict]) -> None:
        self.phones = phones

    def detect(self) -> list[dict[str, Any]]:
        """Identify all shared lines and return structured dicts.

        Algorithm:
        1. Walk every phone's line appearances.
        2. Group by (dn_pattern, partition).
        3. Any DN appearing on 2+ devices is shared.
        4. Build a shared-line dict for each.

        Returns:
            List of shared line dicts with canonical_id, devices, and
            primary_owner information.
        """
        # Map (dn_pattern, partition) -> list of appearance records
        dn_appearances: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for phone in self.phones:
            device_name = phone.get("name", "")
            owner = ref_value(phone.get("ownerUserName"))

            lines_container = phone.get("lines")
            if not lines_container:
                continue

            line_entries = to_list(lines_container, "line")

            for line_entry in line_entries:
                # Speed dials have no dirn — skip them
                dirn = line_entry.get("dirn")
                if dirn is None:
                    continue

                dn_pattern = ref_value(dirn.get("pattern")) if isinstance(dirn, dict) else None
                if not dn_pattern:
                    continue

                partition = ""
                route_partition = dirn.get("routePartitionName") if isinstance(dirn, dict) else None
                if route_partition is not None:
                    partition = ref_value(route_partition) or ""

                line_index_raw = line_entry.get("index")
                try:
                    line_index = int(line_index_raw) if line_index_raw is not None else None
                except (ValueError, TypeError):
                    line_index = None

                # Collect associated endusers for this line appearance
                assoc_endusers_container = line_entry.get("associatedEndusers")
                assoc_endusers: list[str] = []
                if assoc_endusers_container is not None:
                    enduser_entries = to_list(assoc_endusers_container, "enduser")
                    for eu in enduser_entries:
                        eu_id = ref_value(eu.get("userId")) if isinstance(eu, dict) else ref_value(eu)
                        if eu_id:
                            assoc_endusers.append(eu_id)

                dn_appearances[(dn_pattern, partition)].append(
                    {
                        "device_name": device_name,
                        "device_owner": owner,
                        "line_index": line_index,
                        "associated_endusers": assoc_endusers,
                    }
                )

        # Filter to DNs on 2+ devices and build output
        results: list[dict[str, Any]] = []

        for (dn_pattern, partition), appearances in sorted(dn_appearances.items()):
            if len(appearances) < 2:
                continue

            # Determine primary owner: user with DN at line index 1.
            # If multiple at index 1, first one wins.
            primary_owner: str | None = None
            for app in appearances:
                if app["line_index"] == 1 and app["device_owner"] is not None:
                    primary_owner = app["device_owner"]
                    break

            # Aggregate all associated endusers across devices (deduplicated)
            all_endusers: list[str] = []
            seen_endusers: set[str] = set()
            for app in appearances:
                for eu in app["associated_endusers"]:
                    if eu not in seen_endusers:
                        seen_endusers.add(eu)
                        all_endusers.append(eu)

            devices = [
                {
                    "device_name": app["device_name"],
                    "device_owner": app["device_owner"],
                    "line_index": app["line_index"],
                }
                for app in appearances
            ]

            results.append(
                {
                    "canonical_id": f"shared_line:{dn_pattern}:{partition}",
                    "dn": dn_pattern,
                    "partition": partition,
                    "device_count": len(appearances),
                    "devices": devices,
                    "primary_owner": primary_owner,
                    "associated_endusers": all_endusers,
                }
            )

        logger.info("Shared line detection complete: %d shared DNs found", len(results))
        return results
