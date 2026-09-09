#!/usr/bin/env python3
"""sync_classify — the version verdict for a spec sync, from the name lock.

Spec §6, fully mechanical. Ground truth is the generator's OWN output — the
committed lock vs the lock built from the regenerated tree — never a reading
of the spec. Rows are ordered; the first match wins:

  1. an existing name now targets a different endpoint   -> human (silent, breaking)
  2. a command or group is removed                        -> human (breaking)
  3. blast radius: > BLAST_RADIUS_MAX_COMMANDS names changed -> human (green != intended)
  4. a new command group                                  -> minor
  5. new commands, or any regenerated diff at all         -> patch (help text is user-facing)
  6. nothing regenerated                                  -> none (commit specs + snapshot only)

    python -m tools.sync_classify --base origin/main [--json] [--fail-on-human]
    python -m tools.sync_classify --base origin/main --notes .spec-sync --version v1.7.0

Exit codes: 0 = classified; 1 = human, under --fail-on-human only;
2 = input unreadable, nothing classified. Spec §7 rules 1 and 4: what cannot be
read counts as failed, and a tool that cannot read its input refuses rather than
guessing. An unreadable base lock is NOT an empty one — classifying against `{}`
reports every shipping command as new, which reads as a regen that never happened.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOCK = REPO / "tools" / "command_name_lock.json"
# ~3x the largest routine refresh measured in this repo (+16 ops, 2026-07-26).
# Above it, a green gate is not evidence the change was intended.
BLAST_RADIUS_MAX_COMMANDS = 40


def _lock_at(base: str) -> dict | None:
    """The committed lock at `base`, or None if it cannot be read.

    None means "unreadable" — a bad ref, a path absent at that ref, or malformed
    JSON. An empty file returns {}, which is a readable lock declaring no modules.
    """
    out = subprocess.run(["git", "show", f"{base}:tools/command_name_lock.json"],
                         cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        return None
    if not out.stdout.strip():
        return {}
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def _commands_changed(base: str) -> bool | None:
    """Whether src/wxcli/commands/ differs from `base`, or None if git errored.

    `git diff --quiet` exits 0 (same) or 1 (differs); anything else — 128 for a
    bad ref — is an error, not an answer, so it must not read as "changed".
    """
    r = subprocess.run(["git", "diff", "--quiet", base, "--", "src/wxcli/commands/"],
                       cwd=REPO, capture_output=True, text=True)
    if r.returncode not in (0, 1):
        return None
    return r.returncode == 1


def _refuse(what: str, base: str) -> int:
    print(f"sync_classify: cannot read {what} at {base} — refusing to classify (fail closed)",
          file=sys.stderr)
    return 2


def classify(old_lock: dict, new_lock: dict, commands_changed: bool) -> dict:
    old = old_lock.get("modules") or {}
    new = new_lock.get("modules") or {}
    v = {"verdict": "none", "reasons": [], "added": [], "removed": [], "retargeted": [],
         "modules_added": sorted(set(new) - set(old)),
         "modules_removed": sorted(set(old) - set(new))}
    for module in sorted(set(old) & set(new)):
        for name, ops in sorted(old[module].items()):
            if name not in new[module]:
                v["removed"].append(f"{module} {name}")
            elif new[module][name] != ops:
                v["retargeted"].append(f"{module} {name}")
        for name in sorted(set(new[module]) - set(old[module])):
            v["added"].append(f"{module} {name}")
    for module in v["modules_added"]:
        v["added"] += [f"{module} {n}" for n in sorted(new[module])]
    changed = len(v["added"]) + len(v["removed"]) + len(v["retargeted"])
    if v["retargeted"]:
        v["verdict"] = "human"; v["reasons"].append(
            f"{len(v['retargeted'])} existing name(s) now target a different endpoint — pin them back "
            f"(tag_overrides -> command_name_overrides) or a human accepts the rename")
    elif v["removed"] or v["modules_removed"]:
        v["verdict"] = "human"; v["reasons"].append(
            f"{len(v['removed'])} command(s) and {len(v['modules_removed'])} group(s) removed — breaking")
    elif changed > BLAST_RADIUS_MAX_COMMANDS:
        v["verdict"] = "human"; v["reasons"].append(
            f"blast radius: {changed} command names changed > {BLAST_RADIUS_MAX_COMMANDS} — green is not intended")
    elif v["modules_added"]:
        v["verdict"] = "minor"; v["reasons"].append(f"new command group(s): {', '.join(v['modules_added'])}")
    elif commands_changed:
        v["verdict"] = "patch"; v["reasons"].append(
            f"{len(v['added'])} new command(s); regenerated modules differ (fields, enums or help text)")
    else:
        v["reasons"].append("regeneration produced no diff — commit specs + snapshot only, no release")
    return v


def release_notes(verdict: dict, run_dir: Path, version: str) -> str:
    lines = [f"# {version} — weekly spec sync", "",
             f"**Verdict:** {verdict['verdict']} — {'; '.join(verdict['reasons'])}", ""]
    if verdict["modules_added"]:
        lines += ["## New command groups", ""] + [f"- `{m}`" for m in verdict["modules_added"]] + [""]
        routing = run_dir / "routing.md"
        if routing.exists():
            lines += ["### Routing decision", "", routing.read_text().rstrip(), ""]
    if verdict["added"]:
        lines += ["## New commands", ""] + [f"- `{c}`" for c in verdict["added"]] + [""]
    if verdict["removed"] or verdict["retargeted"]:
        lines += ["## BREAKING", ""] + [f"- removed `{c}`" for c in verdict["removed"]] \
              + [f"- retargeted `{c}`" for c in verdict["retargeted"]] + [""]
    delta = run_dir / "spec-delta.txt"
    if delta.exists():
        text = delta.read_text().rstrip()
        lines += ["## Spec delta acknowledged by this sync (check 19)", "", "```", text, "```", ""]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="origin/main")
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-on-human", action="store_true")
    p.add_argument("--notes", metavar="RUN_DIR", help="print release notes built from RUN_DIR")
    p.add_argument("--version", default="vNEXT")
    a = p.parse_args()
    if not LOCK.exists():
        return _refuse(f"the working lock ({LOCK.name})", a.base)
    try:
        new = json.loads(LOCK.read_text())
    except json.JSONDecodeError:
        return _refuse(f"the working lock ({LOCK.name})", a.base)
    old = _lock_at(a.base)
    if old is None:
        return _refuse("the base lock (tools/command_name_lock.json)", a.base)
    commands_changed = _commands_changed(a.base)
    if commands_changed is None:
        return _refuse("the regenerated-modules diff (src/wxcli/commands/)", a.base)
    v = classify(old, new, commands_changed)
    if a.notes:
        print(release_notes(v, Path(a.notes), a.version))
    elif a.json:
        print(json.dumps(v, indent=1))
    else:
        print(f"sync_classify: verdict={v['verdict']}  added={len(v['added'])} removed={len(v['removed'])} "
              f"retargeted={len(v['retargeted'])} groups +{len(v['modules_added'])}/-{len(v['modules_removed'])}")
        for r in v["reasons"]:
            print(f"  {r}")
    return 1 if (a.fail_on_human and v["verdict"] == "human") else 0


if __name__ == "__main__":
    sys.exit(main())
