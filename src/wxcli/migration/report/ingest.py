"""Collector file ingestion — reads SE collector output into raw_data format.

Maps collector JSON keys to the raw_data structure expected by the
normalization pipeline (see discovery.py DiscoveryResult.raw_data contract).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any


# Required top-level keys in a valid collector file.
REQUIRED_KEYS = {"collector_version", "cucm_version", "cluster_name", "collected_at", "objects"}

# Mapping from collector object keys to (extractor_group, sub_key) tuples.
# Source: discovery.py lines 60-70 (DiscoveryResult.raw_data contract).
COLLECTOR_TO_RAW_DATA_MAP: dict[str, tuple[str, str]] = {
    # locations group
    "devicePool": ("locations", "device_pools"),
    "dateTimeGroup": ("locations", "datetime_groups"),
    "cucmLocation": ("locations", "cucm_locations"),
    # users group
    "endUser": ("users", "users"),
    # devices group
    "phone": ("devices", "phones"),
    # routing group
    "routePartition": ("routing", "partitions"),
    "css": ("routing", "css_list"),
    "routePattern": ("routing", "route_patterns"),
    "gateway": ("routing", "gateways"),
    "sipTrunk": ("routing", "sip_trunks"),
    "routeGroup": ("routing", "route_groups"),
    "routeList": ("routing", "route_lists"),
    "transPattern": ("routing", "translation_patterns"),
    # features group
    "huntPilot": ("features", "hunt_pilots"),
    "huntList": ("features", "hunt_lists"),
    "lineGroup": ("features", "line_groups"),
    "ctiRoutePoint": ("features", "cti_route_points"),
    "callPark": ("features", "call_parks"),
    "callPickupGroup": ("features", "pickup_groups"),
    "timeSchedule": ("features", "time_schedules"),
    "timePeriod": ("features", "time_periods"),
    # voicemail group
    "voicemailProfile": ("voicemail", "voicemail_profiles"),
    "voicemailPilot": ("voicemail", "voicemail_pilots"),
}


def ingest_collector_file(
    file_path: str | Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Read a collector file (.json.gz or .json) and return raw_data + metadata.

    The raw_data dict matches the DiscoveryResult.raw_data structure used by
    the normalization pipeline, so it can be written directly to raw_data.json
    and consumed by ``wxcli cucm normalize``.

    Args:
        file_path: Path to collector output file (.json.gz or .json).

    Returns:
        Tuple of (raw_data, metadata) where raw_data matches the
        DiscoveryResult.raw_data contract and metadata contains collector
        header fields (cucm_version, cluster_name, collector_version,
        collected_at).

    Raises:
        ValueError: If the file is missing required keys.
    """
    file_path = Path(file_path)

    if file_path.suffix == ".gz" or file_path.name.endswith(".json.gz"):
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

    # Validate required keys
    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ValueError(
            f"Invalid collector file — missing required keys: {', '.join(sorted(missing))}"
        )

    # Extract metadata from top-level keys
    metadata = {
        "cucm_version": data.get("cucm_version", ""),
        "cluster_name": data.get("cluster_name", ""),
        "collector_version": data.get("collector_version", ""),
        "collected_at": data.get("collected_at", ""),
    }

    objects = data["objects"]

    # Build raw_data structure matching discovery.py contract
    raw_data: dict[str, dict[str, Any]] = {
        "locations": {"device_pools": [], "datetime_groups": [], "cucm_locations": []},
        "users": {"users": []},
        "devices": {"phones": []},
        "routing": {
            "partitions": [], "css_list": [], "route_patterns": [],
            "gateways": [], "sip_trunks": [], "route_groups": [],
            "route_lists": [], "translation_patterns": [],
        },
        "features": {
            "hunt_pilots": [], "hunt_lists": [], "line_groups": [],
            "cti_route_points": [], "call_parks": [], "pickup_groups": [],
            "time_schedules": [], "time_periods": [],
        },
        "voicemail": {"voicemail_profiles": [], "voicemail_pilots": []},
    }

    # Map collector keys to raw_data structure
    for collector_key, (group, sub_key) in COLLECTOR_TO_RAW_DATA_MAP.items():
        if collector_key in objects:
            raw_data[group][sub_key] = objects[collector_key]

    return raw_data, metadata
