from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_FILES = [
    "auto_attendants.json",
    "call_queues.json",
    "hunt_groups.json",
    "voicemail_groups.json",
    "paging_groups.json",
    "call_parks.json",
    "devices.json",
    "workspaces.json",
    "users.json",
    "dial_plans.json",
    "route_groups.json",
    "route_lists.json",
    "trunks.json",
    "numbers.json",
]

DETAIL_DIRS = ["call_queue_details", "outgoing_permissions"]


def load_manifest(collected_dir: Path) -> dict:
    manifest_path = collected_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {collected_dir}")
    return json.loads(manifest_path.read_text())


def validate_collection(collected_dir: Path) -> list[str]:
    errors = []
    for filename in REQUIRED_FILES:
        if not (collected_dir / filename).exists():
            errors.append(f"Missing required file: {filename}")
    return errors


def _load_detail_dir(detail_path: Path) -> dict[str, Any]:
    result = {}
    if detail_path.exists():
        for f in sorted(detail_path.glob("*.json")):
            key = f.stem
            result[key] = json.loads(f.read_text())
    return result


def load_collected_data(collected_dir: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    data["manifest"] = load_manifest(collected_dir)
    for filename in REQUIRED_FILES:
        key = filename.removesuffix(".json")
        filepath = collected_dir / filename
        data[key] = json.loads(filepath.read_text()) if filepath.exists() else []
    for dirname in DETAIL_DIRS:
        data[dirname] = _load_detail_dir(collected_dir / dirname)
    return data
