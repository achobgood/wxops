#!/usr/bin/env python3
"""Spec overlays — additive OpenAPI fragments for endpoints the published spec
omits but the live API actually serves.

Why this exists
---------------
`specs/` is a verbatim mirror of upstream: `tools/update-specs.py` overwrites
each file wholesale from raw.githubusercontent.com. So an endpoint that Cisco's
published spec omits can never be fixed by editing `specs/` — the next pull
erases it. An overlay is a separate, additive fragment merged at LOAD time by
every spec consumer. `specs/` stays byte-identical to upstream, and the
generator still produces the command like any other generated CRUD command.

This is deliberately NOT a hand-written command module: the generator is
perfectly capable of rendering the endpoint (it is plain GET/PUT). The only
thing missing is the spec entry — so the fix targets the spec layer, per the
"never hand-write simple CRUD" rule in tools/CLAUDE.md.

Rules
-----
1. Overlays are ADDITIVE ONLY. An overlay must never modify or delete a path
   upstream already publishes. If upstream ships the path, upstream wins and the
   overlay must be deleted — `superseded_paths()` detects this and the drift
   gate fails on it, so an overlay cannot quietly outlive its purpose.
2. Every overlay path carries `x-wxcli-overlay` provenance: why it exists, and
   the live evidence (method, status code, date) proving the endpoint is real.
   An overlay asserts a server behaviour, so it must cite a real response.

Layout: specs/overlays/<same-name-as-spec>.overlay.json
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OVERLAY_DIR = REPO / "specs" / "overlays"


def overlay_file_for(spec_path: str | Path) -> Path | None:
    """Return the overlay file for a spec, or None when there isn't one."""
    p = OVERLAY_DIR / f"{Path(spec_path).stem}.overlay.json"
    return p if p.exists() else None


def load_overlay(spec_path: str | Path) -> dict:
    f = overlay_file_for(spec_path)
    return json.loads(f.read_text()) if f else {}


def superseded_paths(spec: dict, overlay: dict) -> list[str]:
    """Overlay paths upstream now publishes — the overlay entry must be deleted.

    Called with the RAW upstream spec (pre-merge). Rule 1 above: additive only.
    """
    upstream = set(spec.get("paths", {}))
    return sorted(p for p in overlay.get("paths", {}) if p in upstream)


def merge_overlay(spec: dict, overlay: dict) -> dict:
    """Additively merge `overlay` into `spec` (mutates and returns it).

    Pure and non-raising — callers that need the staleness guard use
    apply_overlay(). Overlay paths are appended after upstream paths, which
    keeps generated command names stable: _derive_command_name() suffixes by
    order of appearance within a tag, so appending cannot rename existing
    commands (tools/CLAUDE.md known issue #18).
    """
    if not overlay:
        return spec
    spec.setdefault("paths", {}).update(overlay.get("paths", {}))
    ocomp = overlay.get("components", {}).get("schemas", {})
    if ocomp:
        spec.setdefault("components", {}).setdefault("schemas", {}).update(ocomp)
    return spec


def apply_overlay(spec: dict, spec_path: str | Path) -> dict:
    """Merge the overlay for `spec_path` into `spec`, enforcing rule 1.

    Raises if the overlay collides with an upstream path — that means upstream
    caught up and the overlay must be deleted rather than silently shadowing
    Cisco's own definition.
    """
    overlay = load_overlay(spec_path)
    if not overlay:
        return spec
    clash = superseded_paths(spec, overlay)
    if clash:
        raise ValueError(
            f"overlay {overlay_file_for(spec_path)} is stale — upstream now "
            f"publishes {clash}. Delete these overlay entries and regenerate."
        )
    return merge_overlay(spec, overlay)


def overlay_summary() -> list[tuple[str, str, str]]:
    """(spec_name, path, reason) for every overlay entry — for reporting."""
    rows = []
    if not OVERLAY_DIR.exists():
        return rows
    for f in sorted(OVERLAY_DIR.glob("*.overlay.json")):
        data = json.loads(f.read_text())
        spec_name = f.name.replace(".overlay.json", ".json")
        for path, methods in data.get("paths", {}).items():
            prov = methods.get("x-wxcli-overlay", {})
            rows.append((spec_name, path, prov.get("reason", "(no reason given)")))
    return rows
