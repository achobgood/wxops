"""Pull and diff the Flow Store spec snapshot.

    python -m tools.flow_store_spec pull [--out specs/webex-cc-flow-store.json] [--stdout]
    python -m tools.flow_store_spec diff [--snapshot specs/webex-cc-flow-store.json] [--exit-code]

The LIVE contract at GET {flow-store base}/v3/api-docs is the only source of truth
(repo rule). After `pull`, `git diff specs/` shows drift; if any, regenerate + retest.
The base URL and token come from wxcli: `get_flow_store_base_url()` and
`resolve_token()` (WEBEX_ACCESS_TOKEN -> WEBEX_TOKEN -> ~/.wxcli/config.json).

`pull` was wxcc's tools/generator/pull_spec.py; `diff` was the `wxcc-flow spec-diff`
command (wxcc/src/wxcc_flow/main.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

from wxcli.auth import resolve_token
from wxcli.config import get_flow_store_base_url

REPO = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO / "specs" / "webex-cc-flow-store.json"
_HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def fetch_spec() -> dict:
    token = resolve_token()
    if not token:
        print("No token. Run 'wxcli configure' or set WEBEX_ACCESS_TOKEN.", file=sys.stderr)
        raise SystemExit(1)
    url = f"{get_flow_store_base_url()}/v3/api-docs"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if resp.status_code == 401:
        print("401 Unauthorized — regenerate the token at developer.webex.com.", file=sys.stderr)
        raise SystemExit(1)
    resp.raise_for_status()
    return resp.json()


def spec_ops(spec: dict) -> dict:
    """Flatten a spec to {(METHOD, path): operation-dict}."""
    ops = {}
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for m in _HTTP_METHODS:
            op = item.get(m)
            if isinstance(op, dict):
                ops[(m.upper(), path)] = op
    return ops


def diff_specs(snap: dict, live: dict):
    """Return (added, removed, changed) op keys, live vs snapshot."""
    old, new = spec_ops(snap), spec_ops(live)
    added = sorted(k for k in new if k not in old)
    removed = sorted(k for k in old if k not in new)
    changed = sorted(
        k for k in new
        if k in old and json.dumps(new[k], sort_keys=True) != json.dumps(old[k], sort_keys=True)
    )
    return added, removed, changed


def _pull(args: argparse.Namespace) -> int:
    spec = fetch_spec()
    n_paths = len(spec.get("paths", {}))
    n_ops = len(spec_ops(spec))
    text = json.dumps(spec, indent=1) + "\n"
    if args.stdout:
        print(text)
    else:
        Path(args.out).write_text(text)
        print(f"Wrote {args.out}  ({n_paths} paths / {n_ops} ops)")
    return 0


def _diff(args: argparse.Namespace) -> int:
    snap_path = Path(args.snapshot)
    if not snap_path.exists():
        print(f"Error: File not found: {args.snapshot}", file=sys.stderr)
        return 1
    snap = json.loads(snap_path.read_text())
    live = fetch_spec()
    if not isinstance(live, dict):
        print("Error: live /v3/api-docs did not return a JSON object.", file=sys.stderr)
        return 1

    added, removed, changed = diff_specs(snap, live)
    old_ops, new_ops = spec_ops(snap), spec_ops(live)
    for m, p in added:
        print(f"+ {m} {p}  ({new_ops[(m, p)].get('operationId', '?')})")
    for m, p in removed:
        print(f"- {m} {p}  ({old_ops[(m, p)].get('operationId', '?')})")
    for m, p in changed:
        print(f"~ {m} {p}  ({new_ops[(m, p)].get('operationId', '?')})")
    print(
        f"Live {len(new_ops)} ops / snapshot {len(old_ops)} ops — "
        f"{len(added)} added, {len(removed)} removed, {len(changed)} changed."
    )
    if not (added or removed or changed):
        print("In sync.")
    elif args.exit_code:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m tools.flow_store_spec",
                                 description="Pull and diff the Flow Store spec snapshot")
    sub = ap.add_subparsers(dest="command", required=True)

    pull = sub.add_parser("pull", help="Pull the live Flow Store spec into specs/")
    pull.add_argument("--out", default=str(SNAPSHOT), help="Snapshot path to write")
    pull.add_argument("--stdout", action="store_true",
                      help="Print the spec instead of writing the snapshot")
    pull.set_defaults(func=_pull)

    diff = sub.add_parser("diff", help="Diff the LIVE contract (GET /v3/api-docs) against the snapshot")
    diff.add_argument("--snapshot", default=str(SNAPSHOT), help="Committed spec snapshot to diff against")
    diff.add_argument("--exit-code", action="store_true",
                      help="Exit 1 when the live contract differs from the snapshot (CI use)")
    diff.set_defaults(func=_diff)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
