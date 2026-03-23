"""Validate extractors against live CUCM 15.0.

Read-only validation — list/get operations only, no writes.
Captures actual zeep dict shapes for fixture correction.

Usage: python3.11 tests/migration/cucm/validate_live_cucm.py
"""

from __future__ import annotations

import json
import sys
import warnings

# Suppress SSL warnings for self-signed certs
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Connection details
HOST = "10.201.123.107"
USERNAME = "admin"
PASSWORD = "c1sco123"
VERSION = "15.0"


def json_safe(obj):
    """Convert zeep objects to JSON-serializable dicts."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(i) for i in obj]
    # zeep objects with __dict__
    if hasattr(obj, "__dict__"):
        return {k: json_safe(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    # zeep objects that are dict-like
    if hasattr(obj, "items"):
        return {k: json_safe(v) for k, v in obj.items()}
    return str(obj)


def dump(label, data, indent=2):
    """Pretty-print a section."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(json_safe(data), indent=indent, default=str))


def main():
    from wxcli.migration.cucm.connection import AXLConnection

    print(f"Connecting to CUCM at {HOST}...")
    conn = AXLConnection(HOST, USERNAME, PASSWORD, version=VERSION)
    print("Connected!")

    # 1. Version detection
    try:
        ver = conn.get_version()
        print(f"CUCM Version: {ver}")
    except Exception as e:
        print(f"Version detection failed: {e}")

    # 2. listDevicePool — check zeep dict shape for reference fields
    print("\n--- listDevicePool ---")
    dps = conn.paginated_list(
        "listDevicePool",
        {"name": "%"},
        {"name": "", "dateTimeSettingName": "", "locationName": "",
         "callManagerGroupName": "", "srstName": "", "regionName": "",
         "mediaResourceListName": ""},
    )
    print(f"Found {len(dps)} device pools")
    if dps:
        dump("First device pool (zeep dict)", dps[0])

    # 3. getDevicePool — full detail
    if dps:
        dp_name = dps[0].get("name") if isinstance(dps[0].get("name"), str) else dps[0]["name"]
        detail = conn.get_detail("getDevicePool", name=dp_name)
        if detail:
            dump(f"getDevicePool({dp_name}) — full detail", detail)

    # 4. listPhone — check phone list shape
    print("\n--- listPhone ---")
    phones = conn.paginated_list(
        "listPhone",
        {"name": "%"},
        {"name": "", "model": "", "ownerUserName": "", "devicePoolName": "",
         "protocol": "", "description": ""},
    )
    print(f"Found {len(phones)} phones")
    if phones:
        dump("First phone (list summary)", phones[0])

    # 5. getPhone — full detail with lines
    if phones:
        phone_name = phones[0].get("name") if isinstance(phones[0].get("name"), str) else phones[0]["name"]
        detail = conn.get_detail("getPhone", name=phone_name)
        if detail:
            # Print just the keys and line structure
            dump(f"getPhone({phone_name}) — top-level keys", list(detail.keys()) if hasattr(detail, "keys") else detail)
            lines = detail.get("lines") if hasattr(detail, "get") else None
            if lines:
                dump("getPhone lines structure", lines)
            owner = detail.get("ownerUserName") if hasattr(detail, "get") else None
            dump("ownerUserName value", owner)
            css = detail.get("callingSearchSpaceName") if hasattr(detail, "get") else None
            dump("callingSearchSpaceName value", css)

    # 6. listCss — check CSS list
    print("\n--- listCss ---")
    css_list = conn.paginated_list(
        "listCss",
        {"name": "%"},
        {"name": "", "description": "", "members": ""},
    )
    print(f"Found {len(css_list)} CSS")

    # 7. getCss — member structure (CRITICAL: index field)
    if css_list:
        css_name = css_list[0].get("name") if isinstance(css_list[0].get("name"), str) else css_list[0]["name"]
        detail = conn.get_detail("getCss", name=css_name)
        if detail:
            dump(f"getCss({css_name}) — full detail", detail)
            members = detail.get("members") if hasattr(detail, "get") else None
            dump("CSS members structure", members)

    # 8. listLocation — verify method and response
    print("\n--- listLocation ---")
    locs = conn.paginated_list(
        "listLocation",
        {"name": "%"},
        {"name": ""},
    )
    print(f"Found {len(locs)} CUCM locations")
    if locs:
        dump("First location", locs[0])

    # 9. listSipTrunk — verify method works
    print("\n--- listSipTrunk ---")
    trunks = conn.paginated_list(
        "listSipTrunk",
        {"name": "%"},
        {"name": "", "description": "", "devicePoolName": "",
         "sipProfileName": "", "securityProfileName": ""},
    )
    print(f"Found {len(trunks)} SIP trunks")
    if trunks:
        dump("First SIP trunk (list)", trunks[0])

    # 10. getSipTrunk — check destination structure
    if trunks:
        trunk_name = trunks[0].get("name") if isinstance(trunks[0].get("name"), str) else trunks[0]["name"]
        detail = conn.get_detail("getSipTrunk", name=trunk_name)
        if detail:
            dest = detail.get("destinations") if hasattr(detail, "get") else None
            dump(f"getSipTrunk({trunk_name}) — destinations structure", dest)
            trunk_type = detail.get("sipTrunkType") if hasattr(detail, "get") else None
            dump("sipTrunkType value", trunk_type)
            max_calls = detail.get("maxNumCalls") if hasattr(detail, "get") else None
            dump("maxNumCalls value", max_calls)

    # 11. listRoutePartition
    print("\n--- listRoutePartition ---")
    parts = conn.paginated_list(
        "listRoutePartition",
        {"name": "%"},
        {"name": "", "description": ""},
    )
    print(f"Found {len(parts)} partitions")

    # 12. listRoutePattern
    print("\n--- listRoutePattern ---")
    rps = conn.paginated_list(
        "listRoutePattern",
        {"pattern": "%"},
        {"pattern": "", "routePartitionName": "", "blockEnable": "",
         "description": "", "calledPartyTransformationMask": "",
         "callingPartyTransformationMask": "", "prefixDigitsOut": "",
         "networkLocation": ""},
    )
    print(f"Found {len(rps)} route patterns")
    if rps:
        dump("First route pattern", rps[0])

    # 13. listGateway — check search field
    print("\n--- listGateway ---")
    gws = conn.paginated_list(
        "listGateway",
        {"domainName": "%"},
        {"domainName": "", "description": "", "product": "", "protocol": ""},
    )
    print(f"Found {len(gws)} gateways")
    if gws:
        dump("First gateway", gws[0])

    # 14. listHuntPilot — expect 0 on this cluster
    print("\n--- listHuntPilot ---")
    try:
        hps = conn.paginated_list(
            "listHuntPilot",
            {"pattern": "%"},
            {"pattern": "", "description": "", "routePartitionName": ""},
        )
        print(f"Found {len(hps)} hunt pilots")
    except Exception as e:
        print(f"listHuntPilot: {e}")

    # 15. listVoiceMailPilot — expect 0
    print("\n--- listVoiceMailPilot ---")
    try:
        vmps = conn.paginated_list(
            "listVoiceMailPilot",
            {"dirn": "%"},
            {"dirn": "", "description": ""},
        )
        print(f"Found {len(vmps)} voicemail pilots")
    except Exception as e:
        print(f"listVoiceMailPilot: {e}")

    print("\n\nValidation complete!")


if __name__ == "__main__":
    main()
