#!/usr/bin/env python3.11
"""Compare a Postman collection export (v2.1) against a local OpenAPI 3.0 spec.

Produces the same gap table as the Postman↔Spec Sync Report.

Usage:
    python3.11 tools/postman_spec_diff.py \
        --spec specs/webex-cloud-calling.json \
        --postman exported-calling.json

    # With skip_tags from field_overrides.yaml:
    python3.11 tools/postman_spec_diff.py \
        --spec specs/webex-cloud-calling.json \
        --postman exported-calling.json \
        --skip-tags tools/field_overrides.yaml
"""
import argparse
import fnmatch
import json
import sys

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def parse_postman_folders(collection: dict) -> dict[str, int]:
    """Walk Postman collection items recursively, return {folder_name: request_count}."""
    folders = {}

    def walk(items, depth=0):
        for item in items:
            children = item.get("item") or item.get("itemRefs") or []
            if children and depth == 0:
                # Top-level folder — count leaf requests
                folders[item["name"]] = count_requests(children)
            elif children:
                walk(children, depth + 1)

    def count_requests(items) -> int:
        total = 0
        for item in items:
            children = item.get("item") or item.get("itemRefs") or []
            if children:
                total += count_requests(children)
            else:
                total += 1
        return total

    root = collection.get("collection", collection)
    items = root.get("item") or root.get("itemRefs") or []
    walk(items)
    return folders


def parse_spec_tags(spec: dict) -> dict[str, int]:
    """Extract {tag: operation_count} from an OpenAPI 3.0 spec."""
    tag_counts: dict[str, int] = {}
    for methods in spec.get("paths", {}).values():
        for method, op in methods.items():
            if method in ("get", "post", "put", "patch", "delete", "head", "options"):
                for tag in op.get("tags", ["Untagged"]):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return tag_counts


def load_skip_tags(path: str) -> list[str]:
    """Load skip_tags patterns from field_overrides.yaml."""
    if not HAS_YAML:
        print("WARNING: PyYAML not installed — skip_tags ignored. pip install pyyaml", file=sys.stderr)
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("skip_tags", [])


def matches_skip(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def classify(postman: dict[str, int], spec: dict[str, int], skip: list[str]):
    rows = []
    for name in sorted(set(list(postman) + list(spec))):
        p = postman.get(name)
        s = spec.get(name)
        skipped = matches_skip(name, skip)

        if p is not None and s is not None:
            if skipped:
                status, notes = "SKIPPED", "In skip_tags"
            elif abs(p - s) > 2:
                status, notes = "COUNT MISMATCH", f"Δ={p - s}"
            else:
                status, notes = "MATCHED", ""
        elif p is not None:
            if skipped:
                status, notes = "SKIPPED", "In skip_tags, not in spec"
            else:
                status, notes = "NEW IN POSTMAN", "No matching spec tag"
        else:
            if skipped:
                status, notes = "SKIPPED", "In skip_tags, not in Postman"
            else:
                status, notes = "MISSING FROM POSTMAN", "Tag in spec, no Postman folder"

        rows.append((name, p if p is not None else "—", s if s is not None else "—", status, notes))
    return rows


def main():
    parser = argparse.ArgumentParser(description="Diff Postman collection vs OpenAPI spec")
    parser.add_argument("--spec", required=True, help="Path to OpenAPI 3.0 JSON spec")
    parser.add_argument("--postman", required=True, help="Path to exported Postman collection JSON (v2.1)")
    parser.add_argument("--skip-tags", help="Path to field_overrides.yaml for skip_tags patterns")
    args = parser.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)
    with open(args.postman) as f:
        postman = json.load(f)

    skip = load_skip_tags(args.skip_tags) if args.skip_tags else []

    pm_folders = parse_postman_folders(postman)
    sp_tags = parse_spec_tags(spec)
    rows = classify(pm_folders, sp_tags, skip)

    order = {"NEW IN POSTMAN": 0, "COUNT MISMATCH": 1, "MISSING FROM POSTMAN": 2, "SKIPPED": 3, "MATCHED": 4}
    rows.sort(key=lambda r: (order.get(r[3], 5), r[0]))

    # Summary
    counts = {}
    for *_, status, _ in rows:
        counts[status] = counts.get(status, 0) + 1

    print(f"Postman folders: {len(pm_folders)} ({sum(pm_folders.values())} requests)")
    print(f"Spec tags: {len(sp_tags)} ({sum(sp_tags.values())} operations)")
    print(f"Matched: {counts.get('MATCHED', 0)}  |  New: {counts.get('NEW IN POSTMAN', 0)}  |  "
          f"Mismatch: {counts.get('COUNT MISMATCH', 0)}  |  Missing: {counts.get('MISSING FROM POSTMAN', 0)}  |  "
          f"Skipped: {counts.get('SKIPPED', 0)}")
    print()

    # Table
    w = max((len(r[0]) for r in rows), default=10)
    hdr = f"{'Folder/Tag':<{w}}  {'PM':>4}  {'Spec':>4}  {'Status':<20}  Notes"
    print(hdr)
    print("-" * len(hdr))
    for name, p, s, status, notes in rows:
        p_str = str(p) if p != "—" else "—"
        s_str = str(s) if s != "—" else "—"
        print(f"{name:<{w}}  {p_str:>4}  {s_str:>4}  {status:<20}  {notes}")


if __name__ == "__main__":
    main()
