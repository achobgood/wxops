#!/usr/bin/env python3.14
"""Atomic spec sync — a spec refresh is not done until the CLI matches it.

Runs (target-architecture A2): update-specs.py -> generate_commands.py --all
for every git-tracked spec (registration manifest updates as a side effect)
-> drift gate report + deliberate-gaps doc. Review the diff, run the test
suite, then land everything as ONE commit:

    python3.14 tools/spec_sync.py [--skip-update] [--run-dir DIR]
    git add -u specs src/wxcli/commands src/wxcli/_playbook tools/spec_semantics.json tools/command_name_lock.json docs/arch/deliberate-gaps.md CLAUDE.md README.md

The untracked dev-only spec (webex-flow-store.json) is never synced here —
regen it manually; the generator auto-applies --dev-only for it.
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

# CC before admin/meetings kept for historical tag-collision safety; the
# per-spec cli_name_overrides (Site, Data Sources) make order non-load-bearing.
PREFERRED_ORDER = [
    "webex-cloud-calling.json",
    "webex-device.json",
    "webex-messaging.json",
    "webex-ucm.json",
    "webex-contact-center.json",
    "webex-admin.json",
    "webex-meetings.json",
]


def run(cmd: list[str], tee: Path | None = None, **kwargs) -> None:
    """Run one step; abort the whole sync on the first non-zero exit.

    `tee` captures stdout+stderr to a run-record file AND echoes it. For the
    snapshot refresh that capture is the point: the refresh prints the
    structural / ID-kind delta it is about to acknowledge, and once the file
    is rewritten that text exists nowhere else (spec §5.4).
    """
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    if tee is None:
        result = subprocess.run(cmd, cwd=REPO, **kwargs)
    else:
        result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, **kwargs)
        out = (result.stdout or "") + (result.stderr or "")
        tee.write_text(out)
        print(out, end="", flush=True)
    if result.returncode != 0:
        print(f"spec-sync: step failed (exit {result.returncode}) — aborting "
              f"before later steps run against inconsistent state", file=sys.stderr)
        sys.exit(result.returncode)


def tracked_specs() -> list[str]:
    # git ls-files with pathspec "specs/*.json" matches files directly in specs/,
    # not in subdirectories. Filter to exclude overlay files (specs/overlays/*.overlay.json).
    out = subprocess.run(["git", "ls-files", "--", "specs/*.json"],
                         capture_output=True, text=True, cwd=REPO, check=True)
    names = [Path(line).name for line in out.stdout.splitlines() if line and not line.endswith(".overlay.json")]
    ordered = [n for n in PREFERRED_ORDER if n in names]
    ordered += sorted(n for n in names if n not in PREFERRED_ORDER)
    return ordered


def repair_published_counts(measured: int | None = None) -> list[str]:
    """Rewrite every 'N command groups' claim check 3 harvests to the measured N.

    Uses the gate's own harvester so the set of claims repaired is exactly the
    set check 3 would fail — no second regex to drift. Only the digits inside
    the harvested span change; prose around them is untouched.
    """
    from tools import drift_check as dc
    if measured is None:
        measured = dc.distinct_command_sets()
    changed: list[str] = []
    by_file: dict[str, list[dict]] = {}
    for claim in dc.harvest_count_claims():
        if claim["kind"] == "command groups" and claim["value"] != measured:
            by_file.setdefault(claim["file"], []).append(claim)
    for rel, claims in by_file.items():
        path = dc.REPO / rel
        lines = path.read_text().splitlines(keepends=True)
        for c in claims:
            i = c["line"] - 1
            fixed = c["text"].replace(str(c["value"]), str(measured), 1)
            lines[i] = lines[i].replace(c["text"], fixed, 1)
        path.write_text("".join(lines))
        changed.append(str(path))
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-update", action="store_true",
                        help="regen from the specs already on disk (no upstream pull)")
    parser.add_argument("--run-dir", default=str(REPO / ".spec-sync"),
                        help="where the run records go (spec-delta.txt, name-lock.txt, gate.txt)")
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_update:
        run([PYTHON, "tools/update-specs.py"])

    for spec in tracked_specs():
        run([PYTHON, "tools/generate_commands.py",
             "--spec", f"specs/{spec}", "--all"],
            env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"})

    # Lock BEFORE snapshot: a moved name aborts the run here, before anything
    # is acknowledged. The refresh is additive and refuses on a move.
    run([PYTHON, "-m", "tools.drift_check", "--refresh-name-lock"],
        tee=run_dir / "name-lock.txt")
    # The delta is captured to disk before the snapshot is rewritten.
    run([PYTHON, "-m", "tools.drift_check", "--refresh-spec-snapshot"],
        tee=run_dir / "spec-delta.txt")
    # Repair BEFORE assemble: assemble.py copies the root CLAUDE.md into the
    # bundled playbook and generates AGENTS.md from it, so a count repaired
    # after the copy leaves the bundle stale and fails the pass bar's
    # "assemble.py leaves no diff" item.
    for path in repair_published_counts():
        print(f"repaired published count in {path}")
    run([PYTHON, "wxcli-dist/assemble.py"])
    # Report, not enforce: the pass bar is the caller's step. Captured so the
    # run record shows what the gate said at the end of the mechanical steps.
    run([PYTHON, "-m", "tools.drift_check", "--write-gaps"], tee=run_dir / "gate.txt")

    print(f"\nspec-sync complete. Records in {run_dir}. Next: the pass bar — "
          "python -m tools.drift_check --enforce; TERM=dumb COLUMNS=400 pytest "
          "tests/ -m 'not live'; git status --porcelain src/wxcli/_playbook must "
          "be empty.")


if __name__ == "__main__":
    main()
