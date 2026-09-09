#!/usr/bin/env python3
"""sync_version — the next vX.Y.Z that both git and PyPI will accept.

    python -m tools.sync_version --level patch|minor [--pypi-json FILE]

Exit 0 and print the version; 1 if the computed version already exists
(should be impossible — asserted anyway); 2 if PyPI cannot be read (never tag
blind: a burned version is permanent).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYPI_URL = "https://pypi.org/pypi/wxcli/json"
RELEASE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def _parse(v: str) -> tuple[int, int, int] | None:
    m = RELEASE.match(v)
    return tuple(int(x) for x in m.groups()) if m else None


def bump(version: str, level: str) -> str:
    major, minor, patch = _parse(version)
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    raise ValueError(f"level must be patch or minor, not {level!r} — a major bump is never automatic")


def next_version(level: str, tags: list[str], pypi: list[str]) -> str:
    seen = [t for t in (_parse(x) for x in [*tags, *pypi]) if t]
    if not seen:
        raise ValueError("no release version found in tags or on PyPI")
    base = ".".join(str(n) for n in max(seen))
    nxt = bump(base, level)
    if _parse(nxt) in seen:
        raise RuntimeError(f"{nxt} already exists")
    return f"v{nxt}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--level", required=True, choices=["patch", "minor"])
    p.add_argument("--pypi-json", help="read PyPI metadata from a file (tests / offline)")
    a = p.parse_args()
    tags = subprocess.run(["git", "tag", "--list", "v*"], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.split()
    try:
        if a.pypi_json:
            meta = json.loads(Path(a.pypi_json).read_text())
        else:
            with urllib.request.urlopen(PYPI_URL, timeout=20) as r:
                meta = json.load(r)
        pypi = list(meta.get("releases", {}))
    except Exception as e:
        print(f"sync_version: cannot read PyPI ({e}) — refusing to choose a version blind", file=sys.stderr)
        return 2
    try:
        print(next_version(a.level, tags, pypi))
    except RuntimeError as e:
        print(f"sync_version: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
