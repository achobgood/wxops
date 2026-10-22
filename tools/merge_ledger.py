#!/usr/bin/env python3
"""File-by-file ledger for the Webex Ops merge (wxcc-agent-builder -> wxops).

Every file in both origin repos gets one row, and every row ends with a fate.
Nothing may disappear unaccounted (spec
docs/superpowers/specs/2026-10-18-webex-ops-merge-design.md §7.1, anti-goal A1).

    python tools/merge_ledger.py build --wxcc-commit SHA --wxops-commit SHA \
        [--local-only FILE] [--ref KIND:NAME:REF ...] --out PATH
    python tools/merge_ledger.py check PATH [--final] [--local]
    python tools/merge_ledger.py set PATH --origin O --origin-path P --fate F \
        [--kind tracked] [--current-path C] [--note N]

`check` without `--local` is what CI runs: CI clones carry neither the ignored
local-only files nor the wxcc-archive refs, so those rows are only verified
with `--local` on a real checkout.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FATES = ("pending", "kept", "merged", "superseded", "deletion-approved", "not-carried")
KINDS = ("tracked", "local-only", "branch", "tag")
ORIGINS = ("wxcc", "wxops")
# Fates whose rows may keep a wxcc/ current_path under --final (nothing is carried).
FINAL_EXEMPT = ("deletion-approved", "not-carried")
# Generated bundles and generated command code are rebuilt, not carried (spec §7.1).
EXCLUDE_GLOBS = ("src/wxcc_flow/_playbook/**", "src/wxcli/_playbook/**",
                 "src/wxcc_flow/generated/**")
COLUMNS = ("origin", "origin_path", "kind", "current_path", "fate", "note")
HELD_PREFIX = "held:"
HELD_NOTE = "not copied — secret/personal; Adam decides"
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class Row:
    origin: str  # "wxcc" or "wxops"
    origin_path: str
    kind: str
    current_path: str
    fate: str
    note: str


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _safe(path: str) -> str:
    # Reject anything str.splitlines() would break on (\r, \x0c, \x85,  …),
    # not just \t/\n: one ledger row must stay exactly one line.
    if "\t" in path or (path and path.splitlines() != [path]):
        raise ValueError(f"unsafe path: {path!r}")
    return path


def origin_files(repo: Path, commit: str) -> list[str]:
    """Every file in `commit`, minus EXCLUDE_GLOBS, sorted."""
    paths = [_safe(p) for p in _git(repo, "ls-tree", "-r", "-z", "--name-only", commit)
             .split("\0") if p]
    return sorted(p for p in paths
                  if not any(fnmatch.fnmatch(p, g) for g in EXCLUDE_GLOBS))


def build_rows(repo: Path, wxcc_commit: str, wxops_commit: str,
               local_only: list[str], refs: list[tuple[str, str, str]]) -> list[Row]:
    rows = [Row("wxcc", p, "tracked", "wxcc/" + p, "pending", "")
            for p in origin_files(repo, wxcc_commit)]
    rows += [Row("wxops", p, "tracked", p, "pending", "")
             for p in origin_files(repo, wxops_commit)]
    for entry in local_only:
        if entry.startswith(HELD_PREFIX):
            path = _safe(entry[len(HELD_PREFIX):])
            rows.append(Row("wxcc", path, "local-only", "", "pending", HELD_NOTE))
        else:
            rows.append(Row("wxcc", _safe(entry), "local-only", "wxcc/" + entry,
                            "pending", ""))
    rows += [Row("wxcc", name, kind, ref, "pending", "") for kind, name, ref in refs]
    return rows


def write_ledger(path: Path, header: dict[str, str], rows: list[Row]) -> None:
    lines = [f"# {k}={v}" for k, v in header.items()]
    lines.append("\t".join(COLUMNS))
    for r in rows:
        fields = [r.origin, r.origin_path, r.kind, r.current_path, r.fate, r.note]
        for f in fields:
            _safe(f)
        lines.append("\t".join(fields))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_ledger(path: Path) -> tuple[dict[str, str], list[Row]]:
    header: dict[str, str] = {}
    rows: list[Row] = []
    with open(path, encoding="utf-8", newline="") as fh:
        lines = fh.read().split("\n")
    for n, line in enumerate(lines, 1):
        if line.startswith("# "):
            key, _, value = line[2:].partition("=")
            header[key] = value
        elif line == "\t".join(COLUMNS) or line == "\t".join(COLUMNS[:-1]) or not line:
            continue
        else:
            fields = line.split("\t")
            if len(fields) == len(COLUMNS) - 1:  # an editor trimmed the empty note's tab
                fields.append("")
            if len(fields) != len(COLUMNS):
                raise ValueError(f"line {n}: expected {len(COLUMNS)} fields, got {len(fields)}")
            rows.append(Row(*fields))
    return header, rows


def _row_errors(row: Row, tracked_now: set[str]) -> list[str]:
    """Per-row rules shared by `check` and `set`: origin, kind, fate, path, note, approval."""
    errors: list[str] = []
    if row.origin not in ORIGINS:
        errors.append(f"unknown origin '{row.origin}'")
    if row.kind not in KINDS:
        errors.append(f"unknown kind '{row.kind}'")
    if row.fate not in FATES:
        errors.append(f"unknown fate '{row.fate}'")
        return errors
    if row.fate in ("kept", "merged", "superseded"):
        if not row.current_path or (row.kind == "tracked"
                                    and row.current_path not in tracked_now):
            errors.append("current_path missing")
    if row.fate in ("merged", "superseded") and not row.note:
        errors.append(f"note required for {row.fate}")
    if row.fate in ("deletion-approved", "not-carried") and not (
            "Adam" in row.note and _DATE.search(row.note)):
        errors.append("needs Adam's approval and a date")
    return errors


def set_row(rows: list[Row], *, origin: str, kind: str, origin_path: str, fate: str,
            current_path: str | None, note: str | None) -> list[Row]:
    """Return `rows` with the one row keyed (origin, kind, origin_path) updated.

    A None field keeps its old value. Raises KeyError if no row matches.
    """
    for i, r in enumerate(rows):
        if (r.origin, r.kind, r.origin_path) == (origin, kind, origin_path):
            updated = dataclasses.replace(
                r, fate=fate,
                current_path=r.current_path if current_path is None else current_path,
                note=r.note if note is None else note)
            return rows[:i] + [updated] + rows[i + 1:]
    raise KeyError(f"no such row: {origin}:{kind}:{origin_path}")


def check(repo: Path, header: dict[str, str], rows: list[Row], *,
          final: bool, local: bool) -> list[str]:
    errors: list[str] = []

    def err(r: Row | tuple[str, str], msg: str) -> None:
        origin, path = (r.origin, r.origin_path) if isinstance(r, Row) else r
        errors.append(f"ERROR {origin}:{path}: {msg}")

    for origin in ("wxcc", "wxops"):
        expected = set(origin_files(repo, header[f"{origin}_commit"]))
        actual = {r.origin_path for r in rows if r.origin == origin and r.kind == "tracked"}
        for p in sorted(expected - actual):
            err((origin, p), "no ledger row")
        for p in sorted(actual - expected):
            err((origin, p), "not in origin commit")

    tracked_now = set(_git(repo, "ls-files", "-z").split("\0"))
    seen: set[tuple[str, str, str]] = set()
    for r in rows:
        key = (r.origin, r.kind, r.origin_path)
        if key in seen:
            err(r, "duplicate row")
        seen.add(key)
        for msg in _row_errors(r, tracked_now):
            err(r, msg)
        if r.fate not in FATES:
            continue
        if final:
            if r.fate == "pending":
                err(r, "still pending")
            if r.current_path.startswith("wxcc/") and r.fate not in FINAL_EXEMPT:
                err(r, "still under wxcc/")
        if local and r.current_path:
            if r.kind == "local-only" and not (repo / r.current_path).exists():
                err(r, "not on disk")
            if r.kind in ("branch", "tag") and subprocess.run(
                    ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
                     r.current_path], capture_output=True).returncode != 0:
                err(r, "ref missing")
    return errors


def _parse_ref(value: str) -> tuple[str, str, str]:
    kind, name, ref = value.split(":", 2)
    if kind not in KINDS:
        raise argparse.ArgumentTypeError(f"unknown ref kind: {kind}")
    return kind, name, ref


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="write a fresh all-pending ledger")
    b.add_argument("--wxcc-commit", required=True)
    b.add_argument("--wxops-commit", required=True)
    b.add_argument("--local-only", type=Path,
                   help="file of wxcc-relative paths; 'held:' lines are not copied")
    b.add_argument("--ref", action="append", default=[], type=_parse_ref,
                   help="KIND:NAME:REF, repeatable")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--repo", type=Path, default=Path("."))
    c = sub.add_parser("check", help="verify every row has a valid fate")
    c.add_argument("path", type=Path)
    c.add_argument("--final", action="store_true", help="no pending rows, nothing under wxcc/")
    c.add_argument("--local", action="store_true",
                   help="also verify local-only files and archive refs exist")
    c.add_argument("--repo", type=Path, default=Path("."))
    s = sub.add_parser("set", help="update the fate of one row")
    s.add_argument("path", type=Path)
    s.add_argument("--origin", required=True, choices=ORIGINS)
    s.add_argument("--origin-path", required=True)
    s.add_argument("--fate", required=True)
    s.add_argument("--kind", default="tracked")
    s.add_argument("--current-path")
    s.add_argument("--note")
    s.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    if args.cmd == "build":
        local = []
        if args.local_only:
            text = args.local_only.read_text(encoding="utf-8")
            local = [ln.strip() for ln in text.splitlines()
                     if ln.strip() and not ln.startswith("# ")]
        rows = build_rows(args.repo, args.wxcc_commit, args.wxops_commit, local, args.ref)
        header = {"wxcc_commit": args.wxcc_commit, "wxops_commit": args.wxops_commit,
                  "built": datetime.date.today().isoformat()}
        write_ledger(args.out, header, rows)
        print(f"ledger: wrote {len(rows)} rows to {args.out}")
        return 0

    try:
        header, rows = read_ledger(args.path)
    except ValueError as exc:
        print(f"ERROR {exc}")
        return 1
    try:
        repo = Path(_git(args.repo, "rev-parse", "--show-toplevel").strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        repo = args.repo

    if args.cmd == "set":
        try:
            new_rows = set_row(rows, origin=args.origin, kind=args.kind,
                               origin_path=args.origin_path, fate=args.fate,
                               current_path=args.current_path, note=args.note)
        except KeyError as exc:
            print(f"ERROR {exc.args[0]}")
            return 1
        tracked_now = set(_git(repo, "ls-files", "-z").split("\0"))
        updated = next(r for r in new_rows if (r.origin, r.kind, r.origin_path)
                       == (args.origin, args.kind, args.origin_path))
        problems = _row_errors(updated, tracked_now)
        for msg in problems:
            print(f"ERROR {args.origin}:{args.origin_path}: {msg}")
        if problems:
            return 1
        write_ledger(args.path, header, new_rows)
        print(f"ledger: set {args.origin}:{args.origin_path} -> {args.fate}")
        return 0

    errors = check(repo, header, rows, final=args.final, local=args.local)
    for e in errors:
        print(e)
    if errors:
        print(f"ledger: {len(errors)} errors in {len(rows)} rows")
        return 1
    pending = sum(r.fate == "pending" for r in rows)
    print(f"ledger: {len(rows)} rows, {pending} pending")
    return 0


if __name__ == "__main__":
    sys.exit(main())
