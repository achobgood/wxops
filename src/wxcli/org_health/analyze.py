"""Org health analyzer — load collected data, run checks, produce results.

Usage:
    python3.14 -m wxcli.org_health.analyze <collected-dir> --output <results-dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wxcli.org_health.collector import load_collected_data, validate_collection
from wxcli.org_health.checks import run_all_checks
from wxcli.org_health.models import CategoryScore, HealthResult, OrgStats

CATEGORY_DISPLAY_NAMES = {
    "feature_utilization": "Feature Utilization",
    "device_health": "Device Health",
    "security": "Security Posture",
    "routing": "Routing Hygiene",
}


def _count_locations(data: dict) -> int:
    locations: set[str] = set()
    for item_list_key in ("users", "devices", "auto_attendants", "call_queues", "hunt_groups"):
        for item in data.get(item_list_key, []):
            loc = item.get("locationName") or item.get("location", {}).get("name")
            if loc:
                locations.add(loc)
    return len(locations) if locations else 0


def run_analysis(collected_dir: Path) -> HealthResult:
    data = load_collected_data(collected_dir)
    manifest = data["manifest"]
    findings = run_all_checks(data)

    categories = {}
    for cat_key, display_name in CATEGORY_DISPLAY_NAMES.items():
        cat_findings = [f for f in findings if f.category == cat_key]
        categories[cat_key] = CategoryScore.from_findings(cat_key, display_name, cat_findings)

    stats = OrgStats(
        total_users=len(data.get("users", [])),
        total_devices=len(data.get("devices", [])),
        total_auto_attendants=len(data.get("auto_attendants", [])),
        total_call_queues=len(data.get("call_queues", [])),
        total_hunt_groups=len(data.get("hunt_groups", [])),
        total_trunks=len(data.get("trunks", [])),
        total_locations=_count_locations(data),
        sampled_users_for_permissions=manifest.get("sampled_users_for_permissions", 0),
    )

    return HealthResult(
        org_name=manifest.get("org_name", "Unknown"),
        org_id=manifest.get("org_id", ""),
        collected_at=manifest.get("collected_at", ""),
        categories=categories,
        findings=findings,
        stats=stats,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze collected org health data")
    parser.add_argument("collected_dir", type=Path, help="Path to collected/ directory")
    parser.add_argument("--output", type=Path, required=True, help="Path to results/ directory")
    args = parser.parse_args()

    errors = validate_collection(args.collected_dir)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    result = run_analysis(args.collected_dir)

    args.output.mkdir(parents=True, exist_ok=True)
    results_path = args.output / "results.json"
    results_path.write_text(json.dumps(result.to_dict(), indent=2))
    print(f"Results written to {results_path}")
    print(f"  Findings: {len(result.findings)} total")
    for cat_key, cat in result.categories.items():
        total = cat.high_count + cat.medium_count + cat.low_count + cat.info_count
        if total > 0:
            print(f"  {cat.display_name}: {total} findings ({cat.high_count} HIGH, {cat.medium_count} MEDIUM, {cat.low_count} LOW)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
