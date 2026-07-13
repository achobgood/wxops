#!/usr/bin/env python3
"""Verify that a built wxcli wheel ships a usable Claude/Codex playbook.

This intentionally imports only the standard library.  It runs the console
script from a new virtual environment and changes into a temporary directory,
so success cannot come from the checkout, an editable install, or PYTHONPATH.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


GROUNDING_MARKER = "Never answer any question about Webex Calling from training data alone"
SHARED_DOCS = (
    "docs/reference/authentication.md",
    "docs/knowledge-base/migration/kb-webex-limits.md",
    "docs/runbooks/cucm-migration/operator-runbook.md",
    "docs/runbooks/cucm-migration/decision-guide.md",
    "docs/runbooks/cucm-migration/tuning-reference.md",
)
INTERNAL_ONLY_DOC = "docs/runbooks/cucm-migration/self-review-findings.md"


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _assert_exists(root: Path, relative_paths: tuple[str, ...]) -> None:
    missing = [rel for rel in relative_paths if not (root / rel).exists()]
    if missing:
        raise AssertionError(f"{root} is missing: {', '.join(missing)}")


def _assert_populated_directory(root: Path, relative_path: str) -> None:
    directory = root / relative_path
    if not directory.is_dir() or not any(path.is_file() for path in directory.rglob("*")):
        raise AssertionError(f"{root} is missing populated {relative_path}/")


def _assert_manifest(root: Path, profile: str) -> None:
    path = root / f".{profile}/.wxops-manifest.json"
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AssertionError(f"invalid {profile} manifest at {path}: {exc}") from exc
    if manifest.get("wxops_playbook") is not True or manifest.get("profile") != profile:
        raise AssertionError(f"unexpected {profile} manifest at {path}: {manifest!r}")
    if not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        raise AssertionError(f"{profile} manifest has no owned files: {path}")


def _assert_shared_docs(root: Path) -> None:
    _assert_exists(root, SHARED_DOCS)
    if (root / INTERNAL_ONLY_DOC).exists():
        raise AssertionError(f"internal-only document shipped: {root / INTERNAL_ONLY_DOC}")


def _assert_claude_only(root: Path) -> None:
    _assert_exists(root, ("CLAUDE.md", ".claude/.wxops-manifest.json"))
    for relative_path in (".claude/agents", ".claude/skills", ".claude/rules"):
        _assert_populated_directory(root, relative_path)
    _assert_manifest(root, "claude")
    _assert_shared_docs(root)
    for forbidden in ("AGENTS.md", ".codex"):
        if (root / forbidden).exists():
            raise AssertionError(f"Claude-only profile unexpectedly contains {forbidden}")


def _assert_codex_only(root: Path) -> None:
    _assert_exists(root, ("AGENTS.md", ".codex/.wxops-manifest.json"))
    for relative_path in (".codex/agents", ".codex/skills", ".codex/rules"):
        _assert_populated_directory(root, relative_path)
    _assert_manifest(root, "codex")
    _assert_shared_docs(root)
    for forbidden in ("CLAUDE.md", ".claude"):
        if (root / forbidden).exists():
            raise AssertionError(f"Codex-only profile unexpectedly contains {forbidden}")


def _assert_dual_profile(root: Path) -> None:
    _assert_exists(root, (
        "CLAUDE.md", "AGENTS.md", ".claude/.wxops-manifest.json", ".codex/.wxops-manifest.json",
    ))
    _assert_manifest(root, "claude")
    _assert_manifest(root, "codex")
    _assert_shared_docs(root)

    agent_files = sorted((root / ".codex" / "agents").glob("*.toml"))
    if not agent_files:
        raise AssertionError("dual profile has no generated Codex agent TOML files")
    for path in agent_files:
        with path.open("rb") as fh:
            tomllib.load(fh)
    if GROUNDING_MARKER not in (root / "AGENTS.md").read_text():
        raise AssertionError("generated AGENTS.md lost the mandatory grounding rule")


def _wheel_from(path: Path) -> Path:
    if path.is_file() and path.name.startswith("wxcli-") and path.suffix == ".whl":
        return path.resolve()
    wheels = sorted(path.glob("wxcli-*.whl")) if path.is_dir() else []
    if len(wheels) != 1:
        raise AssertionError(f"expected a wxcli wheel or one in {path}, found {wheels}")
    return wheels[0].resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, help="built wxcli wheel (or a directory containing one)")
    args = parser.parse_args()
    wheel = _wheel_from(args.wheel)

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="wxcli-wheel-smoke-") as temp:
        root = Path(temp)
        venv = root / "venv"
        _run([sys.executable, "-m", "venv", str(venv)], cwd=root, env=env)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        wxcli = venv / ("Scripts/wxcli.exe" if os.name == "nt" else "bin/wxcli")
        # The wheel is the only wxcli artifact installed here. Its declared
        # dependencies may be resolved normally; no repository install occurs.
        _run([str(python), "-m", "pip", "install", "--disable-pip-version-check", str(wheel)],
             cwd=root, env=env)

        claude = root / "claude"
        codex = root / "codex"
        both = root / "both"
        _run([str(wxcli), "init", str(claude), "--claude-only", "--yes"], cwd=root, env=env)
        _run([str(wxcli), "init", str(codex), "--codex-only", "--yes"], cwd=root, env=env)
        _run([str(wxcli), "init", str(both), "--yes"], cwd=root, env=env)

        _assert_claude_only(claude)
        _assert_codex_only(codex)
        _assert_dual_profile(both)
    print("Wheel playbook smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
