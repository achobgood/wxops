#!/usr/bin/env python3.14
"""Atomic spec sync — a spec refresh is not done until the CLI matches it.

Runs (target-architecture A2): update-specs.py -> generate_commands.py --all
for every git-tracked spec (registration manifest updates as a side effect)
-> drift gate report + deliberate-gaps doc. Review the diff, run the test
suite, then land everything as ONE commit:

    python3.14 tools/spec_sync.py [--skip-update]
    git add -u specs src/wxcli/commands docs/arch/deliberate-gaps.md && git commit

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


def run(cmd: list[str], **kwargs) -> None:
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=REPO, **kwargs)
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-update", action="store_true",
                        help="regen from the specs already on disk (no upstream pull)")
    args = parser.parse_args()

    if not args.skip_update:
        run([PYTHON, "tools/update-specs.py"])

    for spec in tracked_specs():
        run([PYTHON, "tools/generate_commands.py",
             "--spec", f"specs/{spec}", "--all"],
            env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"})

    run([PYTHON, "tools/drift_check.py", "--write-gaps"])

    print("\nspec-sync complete. Next: review the diff (especially "
          "src/wxcli/commands/_registry.py), run the test suite, and land "
          "one commit: chore(specs): sync specs + regen (<date>).")


if __name__ == "__main__":
    main()
