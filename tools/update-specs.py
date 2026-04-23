#!/usr/bin/env python3.14
"""
Pull latest Webex OpenAPI specs from the official GitHub repo and update local copies.

Usage:
    python3.14 tools/update-specs.py           # update + report
    python3.14 tools/update-specs.py --dry-run # report only, no writes
    python3.14 tools/update-specs.py --check   # exit 1 if any spec is out of date
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO_RAW = "https://raw.githubusercontent.com/webex/webex-openapi-specs/main/public-spec"

# GitHub filename → local filename (only entries that differ or are new)
SPEC_MAP = {
    "webex-admin.json":         "webex-admin.json",
    "webex-cloud-calling.json": "webex-cloud-calling.json",
    "webex-contact-center.json":"webex-contact-center.json",
    "webex-device.json":        "webex-device.json",
    "webex-meeting.json":       "webex-meetings.json",   # GitHub is singular
    "webex-messaging.json":     "webex-messaging.json",
    "webex-ucm.json":           "webex-ucm.json",
    # Excluded — not part of this project's scope:
    # "webex-broadworks.json":  "webex-broadworks.json",
    # "webex-wholesale.json":   "webex-wholesale.json",
}

SPECS_DIR = Path(__file__).parent.parent / "specs"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def path_count(spec: dict) -> int:
    return len(spec.get("paths", {}))


def path_diff(old: dict, new: dict) -> tuple[list[str], list[str]]:
    old_paths = set(old.get("paths", {}).keys())
    new_paths = set(new.get("paths", {}).keys())
    return sorted(new_paths - old_paths), sorted(old_paths - new_paths)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    parser.add_argument("--check", action="store_true", help="Exit 1 if any spec is stale")
    args = parser.parse_args()

    changed = []
    added = []
    errors = []

    for gh_name, local_name in SPEC_MAP.items():
        local_path = SPECS_DIR / local_name
        url = f"{REPO_RAW}/{gh_name}"

        try:
            remote_bytes = fetch(url)
        except Exception as e:
            errors.append(f"  {gh_name}: fetch failed — {e}")
            continue

        if not local_path.exists():
            remote_spec = json.loads(remote_bytes)
            n = path_count(remote_spec)
            print(f"  NEW  {local_name} ({n} paths)")
            added.append(local_name)
            if not args.dry_run:
                local_path.write_bytes(remote_bytes)
            continue

        local_bytes = local_path.read_bytes()
        if sha256(remote_bytes) == sha256(local_bytes):
            print(f"  OK   {local_name}")
            continue

        local_spec = json.loads(local_bytes)
        remote_spec = json.loads(remote_bytes)
        new_paths, removed_paths = path_diff(local_spec, remote_spec)
        old_n = path_count(local_spec)
        new_n = path_count(remote_spec)

        summary = f"{old_n} → {new_n} paths"
        if new_paths:
            summary += f", +{len(new_paths)} added"
        if removed_paths:
            summary += f", -{len(removed_paths)} removed"

        print(f"  DIFF {local_name} ({summary})")
        for p in new_paths:
            print(f"       + {p}")
        for p in removed_paths:
            print(f"       - {p}")

        changed.append(local_name)
        if not args.dry_run:
            local_path.write_bytes(remote_bytes)

    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)

    total_changed = len(changed) + len(added)
    print(f"\n{total_changed} spec(s) updated, {len(errors)} error(s)")

    if total_changed:
        files = ", ".join(changed + added)
        print(f"Files: {files}")
        if args.dry_run:
            print("(dry-run — no files written)")
        else:
            print("Run `make regen` or regenerate affected command groups.")

    if args.check and total_changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
