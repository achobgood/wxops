#!/usr/bin/env python3
"""sync_guard — the unattended spec sync may not edit what the gate exempts.

Spec §5.5: every check has a legitimate escape hatch, and each is a writable
line whose justification is checked by a human, not a machine. An agent told
to "make the gate green" therefore has a cheat for every finding. This tool
converts that into a hard stop: the run fails if its own diff (vs a base ref)
touches any forbidden surface. It needs no judgement.

    python -m tools.sync_guard diff --base origin/main   # 0 clean, 1 findings, 2 crash
    python -m tools.sync_guard enabled                    # 0 enabled, 3 disabled, 2 unreadable

Allowed for the agent: generated artifacts, docs, skills, the check-19
snapshot, ADDITIVE lock changes, and two override keys (cli_name_overrides,
and command_name_overrides inside tag_overrides) — pins are reactive and the
agent must be able to write one. Everything else in field_overrides.yaml is a
definition of what passes.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONTRACT = REPO / "docs" / "spec-sync-contract.md"

FORBIDDEN_PATHS: tuple[str, ...] = (
    "tools/drift_check.py",
    "tools/drift_check_allowlist.txt",
    "tools/sync_guard.py",
    "tools/sync_classify.py",
    "tools/sync_version.py",
    "tools/generate_commands.py",
    "tools/openapi_parser.py",
    "tools/command_renderer.py",
    "tools/spec_sync.py",
    "tools/update-specs.py",
    ".github/workflows/",
    "docs/spec-sync-contract.md",
    "tests/",
    "tools/sync_*.py",
)
# The check is deny-by-default off ALLOWED_YAML_KEYS: every top-level key NOT in
# ALLOWED is forbidden. This tuple names the ones the spec calls out, for the contract to cite.
FORBIDDEN_YAML_KEYS: tuple[str, ...] = (
    "skip_tags", "keep_endpoints", "naming_ack", "verb_semantics_ack",
    "inert_tag_ack", "undeclared_paging_ack", "spec_authority",
    "tag_op_excludes", "omit_query_params", "auto_inject_from_config",
)
ALLOWED_YAML_KEYS: tuple[str, ...] = ("cli_name_overrides", "tag_overrides")
ALLOWED_TAG_OVERRIDE_SUBKEYS: tuple[str, ...] = ("command_name_overrides",)
OUT_OF_SCOPE_HEADING = re.compile(r"out.of.skill.scope", re.IGNORECASE)
PIPELINE_LINE = re.compile(r"^\*\*Pipeline:\*\*\s*(enabled|disabled)\b", re.M)


def _git(args: list[str], repo: Path) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=True).stdout


def changed_paths(base: str, repo: Path = REPO) -> list[str]:
    """Tracked paths that differ from BASE (working tree, not just index) plus untracked files."""
    # --no-renames: rename detection would report only the NEW path, so moving a
    # forbidden file (or a test out of tests/) would otherwise pass the guard clean.
    tracked = _git(["diff", "--no-renames", "--name-only", base], repo).split()
    untracked = [line[3:] for line in _git(["status", "--porcelain", "--untracked-files=all"], repo).splitlines()
                 if line.startswith("?? ")]
    return sorted(set(tracked) | set(untracked))


def _show(base: str, path: str, repo: Path) -> str:
    try:
        return _git(["show", f"{base}:{path}"], repo)
    except subprocess.CalledProcessError:
        return ""


def path_findings(paths: list[str]) -> list[str]:
    return [f"forbidden path edited: {p}" for p in paths
            if any(p == f or (f.endswith("/") and p.startswith(f))
                   or ("*" in f and fnmatch.fnmatch(p, f))
                   for f in FORBIDDEN_PATHS)]


def yaml_key_findings(old_text: str, new_text: str) -> list[str]:
    old = yaml.safe_load(old_text) or {}
    new = yaml.safe_load(new_text) or {}
    out = []
    for key in sorted(set(old) | set(new)):
        if key in ALLOWED_YAML_KEYS:
            continue
        if old.get(key) != new.get(key):
            verb = "added" if key not in old else "removed" if key not in new else "changed"
            out.append(f"field_overrides.yaml: forbidden key `{key}` {verb}")
    # Inside tag_overrides only command_name_overrides may change.
    o_t, n_t = old.get("tag_overrides") or {}, new.get("tag_overrides") or {}
    for spec in sorted(set(o_t) | set(n_t)):
        o_s, n_s = o_t.get(spec) or {}, n_t.get(spec) or {}
        for tag in sorted(set(o_s) | set(n_s)):
            o_g, n_g = o_s.get(tag) or {}, n_s.get(tag) or {}
            for sub in sorted(set(o_g) | set(n_g)):
                if sub in ALLOWED_TAG_OVERRIDE_SUBKEYS:
                    continue
                if o_g.get(sub) != n_g.get(sub):
                    out.append(f"field_overrides.yaml: tag_overrides[{spec}][{tag!r}].{sub} changed "
                               f"(only command_name_overrides may change unattended)")
    return out


def _out_of_scope_section(text: str) -> str:
    keep, in_section = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            in_section = bool(OUT_OF_SCOPE_HEADING.search(line))
            continue
        if in_section:
            keep.append(line)
    return "\n".join(keep)


def out_of_scope_findings(old_text: str, new_text: str) -> list[str]:
    if _out_of_scope_section(old_text) != _out_of_scope_section(new_text):
        return ["CLAUDE.md: the Out-of-Skill-Scope Command Groups section changed"]
    return []


def lock_findings(old_text: str, new_text: str) -> list[str]:
    """Every (module, command, ops) in the old lock must survive unchanged."""
    old = (json.loads(old_text) if old_text.strip() else {}).get("modules") or {}
    new = (json.loads(new_text) if new_text.strip() else {}).get("modules") or {}
    out = []
    for module, cmds in old.items():
        if module not in new:
            out.append(f"command_name_lock.json: module `{module}` removed (a group vanished, or --force was used)")
            continue
        for name, ops in cmds.items():
            if name not in new[module]:
                out.append(f"command_name_lock.json: `{module} {name}` removed — a command vanished or was renamed")
            elif new[module][name] != ops:
                out.append(f"command_name_lock.json: `{module} {name}` retargeted {ops} -> {new[module][name]}")
    return out


def guard(base: str, repo: Path = REPO) -> list[str]:
    paths = changed_paths(base, repo)
    findings = path_findings(paths)
    if "tools/field_overrides.yaml" in paths:
        findings += yaml_key_findings(_show(base, "tools/field_overrides.yaml", repo),
                                      (repo / "tools" / "field_overrides.yaml").read_text())
    if "CLAUDE.md" in paths:
        findings += out_of_scope_findings(_show(base, "CLAUDE.md", repo),
                                          (repo / "CLAUDE.md").read_text())
    if "tools/command_name_lock.json" in paths:
        findings += lock_findings(_show(base, "tools/command_name_lock.json", repo),
                                  (repo / "tools" / "command_name_lock.json").read_text())
    return findings


def pipeline_enabled(contract_text: str) -> bool | None:
    m = PIPELINE_LINE.search(contract_text)
    return None if not m else m.group(1) == "enabled"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("diff", help="fail if the diff vs --base touches a forbidden surface")
    d.add_argument("--base", default="origin/main")
    sub.add_parser("enabled", help="read the kill switch in docs/spec-sync-contract.md")
    args = parser.parse_args()
    if args.cmd == "enabled":
        state = pipeline_enabled(CONTRACT.read_text()) if CONTRACT.exists() else None
        if state is None:
            print("sync_guard: no `**Pipeline:** enabled|disabled` line in the contract — "
                  "treating as DISABLED (fail closed)", file=sys.stderr)
            return 2
        print(f"sync_guard: pipeline {'enabled' if state else 'DISABLED'}")
        return 0 if state else 3
    findings = guard(args.base)
    for f in findings:
        print(f"  FORBIDDEN  {f}")
    print(f"sync_guard: {len(findings)} forbidden edit(s) vs {args.base}")
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        print("sync_guard: CRASHED — nothing was checked", file=sys.stderr)
        sys.exit(2)
