"""wxcli init — materialize the bundled Claude Code playbook into a local folder.

The folder layout mirrors the repo (CLAUDE.md, .claude/, docs/reference/), so
Claude Code loads everything natively and no path is rewritten (spec §4.3).
A manifest records every written file; refresh and --uninstall touch ONLY
manifest-owned paths — user files are never clobbered.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import typer

import wxcli
from wxcli import __version__

app = typer.Typer(help="Materialize the bundled playbook (Claude Code + Codex) into a local project folder.")

PROFILES = ("claude", "codex")
# Per-profile manifests. Claude keeps its ORIGINAL location → existing installs
# refresh/uninstall unchanged; Codex adds its own alongside it.
MANIFEST_REL = {
    "claude": Path(".claude") / ".wxops-manifest.json",
    "codex": Path(".codex") / ".wxops-manifest.json",
}


def classify(rel: str) -> str:
    """Which profile owns a bundle-relative path; docs/ etc. are 'shared'."""
    if rel.startswith(".codex/") or rel == "AGENTS.md":
        return "codex"
    if rel.startswith(".claude/") or rel == "CLAUDE.md":
        return "claude"
    return "shared"


def profile_files(bundle_files: dict[str, bytes], profile: str) -> dict[str, bytes]:
    """The subset a profile materializes: its own files plus shared files."""
    return {rel: c for rel, c in bundle_files.items()
            if classify(rel) in (profile, "shared")}


def bundle_root() -> Path:
    """The playbook shipped inside the installed package (test-injectable)."""
    return Path(wxcli.__file__).resolve().parent / "_playbook"


def read_bundle(bundle: Path) -> dict[str, bytes]:
    """posix relpath -> content for every file in the installed bundle."""
    return {
        p.relative_to(bundle).as_posix(): p.read_bytes()
        for p in sorted(bundle.rglob("*")) if p.is_file()
    }


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(folder: Path, profile: str) -> dict | None:
    path = folder / MANIFEST_REL[profile]
    return json.loads(path.read_text()) if path.exists() else None


def save_manifest(folder: Path, profile: str, hashes: dict[str, str]) -> None:
    path = folder / MANIFEST_REL[profile]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"wxops_playbook": True, "profile": profile,
         "version": __version__, "files": hashes}, indent=2
    ))


def _prune_empty_dirs(start: Path, stop: Path) -> None:
    d = start
    while d != stop and d.is_dir():
        try:
            d.rmdir()          # fails (OSError) if non-empty → stop pruning
        except OSError:
            return
        d = d.parent


def apply_bundle(
    folder: Path, bundle_files: dict[str, bytes], owned: dict[str, str]
) -> tuple[list[str], list[str], dict[str, str]]:
    """Write/refresh the bundle. Returns (written, deleted, new_hashes).

    Deletes manifest-owned paths absent from the new bundle (retired skills
    don't linger); never touches paths it doesn't own (spec §4.3).
    """
    written: list[str] = []
    hashes: dict[str, str] = {}
    for rel, content in bundle_files.items():
        dest = folder / rel
        if not dest.exists() or dest.read_bytes() != content:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            written.append(rel)
        hashes[rel] = sha256_hex(content)
    deleted: list[str] = []
    for rel in sorted(set(owned) - set(bundle_files)):
        target = folder / rel
        if target.exists():
            target.unlink()
        deleted.append(rel)
        _prune_empty_dirs(target.parent, folder)
    return written, deleted, hashes


def do_uninstall(folder: Path, profiles: list[str]) -> None:
    """Remove files owned by the targeted profiles, keeping shared files still
    owned by a profile that stays installed."""
    manifests = {p: load_manifest(folder, p) for p in PROFILES}
    present = {p for p, m in manifests.items() if m is not None}
    targets = [p for p in profiles if p in present]
    if not targets:
        typer.echo(f"No wxops manifest in {folder} — nothing to uninstall.", err=True)
        raise typer.Exit(1)
    keep_owned: set[str] = set()
    for p in present - set(targets):
        keep_owned |= set(manifests[p].get("files", {}))
    for p in targets:
        for rel in sorted(manifests[p].get("files", {})):
            if rel in keep_owned:
                continue                          # shared file still owned by a kept profile
            target = folder / rel
            if target.exists():
                target.unlink()
            _prune_empty_dirs(target.parent, folder)
        mpath = folder / MANIFEST_REL[p]
        mpath.unlink(missing_ok=True)
        _prune_empty_dirs(mpath.parent, folder)
    typer.echo(f"Removed the wxops playbook ({', '.join(targets)}) from {folder}. "
               "Files you added were left in place.")


# A single @app.command() with no callback: Typer collapses the app into this
# command, so `wxcli init FOLDER --flags` parses positionals and options together.
# (A group callback would treat post-positional options as subcommand names.)
_START_HINT = {
    "claude": "Open this folder in Claude Code (start a fresh session) — "
              "skills and agents load at session start.",
    "codex": "Open this folder in Codex (`codex` in the folder; trust it when prompted) — "
             "AGENTS.md and .codex/ skills load automatically.",
}


@app.command()
def init(
    folder: Path = typer.Argument(Path("wxcli-playbook"), help="Target playbook folder."),
    claude_only: bool = typer.Option(False, "--claude-only", help="Materialize only the Claude Code playbook."),
    codex_only: bool = typer.Option(False, "--codex-only", help="Materialize only the Codex playbook."),
    force: bool = typer.Option(False, "--force", help="Overwrite collisions / refresh without prompting."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove manifest-owned files, then the manifest(s)."),
):
    """Materialize the bundled playbook (Claude Code + Codex) into FOLDER."""
    folder = folder.resolve()
    if claude_only and codex_only:
        typer.echo("Use at most one of --claude-only / --codex-only.", err=True)
        raise typer.Exit(1)
    selected = ["claude"] if claude_only else ["codex"] if codex_only else list(PROFILES)

    if uninstall:
        do_uninstall(folder, selected)
        return

    bundle = bundle_root()
    if not bundle.is_dir():
        typer.echo("Bundled playbook not found in this wxcli install.", err=True)
        raise typer.Exit(1)
    all_files = read_bundle(bundle)
    manifests = {p: load_manifest(folder, p) for p in selected}

    sel_files: dict[str, bytes] = {}
    for p in selected:
        sel_files.update(profile_files(all_files, p))

    if all(m is None for m in manifests.values()):        # fresh for the selected profiles
        collisions = sorted(rel for rel in sel_files if (folder / rel).exists())
        if collisions and not force:
            typer.echo(f"{folder} already contains files the playbook would overwrite:", err=True)
            for rel in collisions:
                typer.echo(f"  {rel}", err=True)
            typer.echo("Re-run with --force to overwrite them, or choose an empty folder.", err=True)
            raise typer.Exit(1)
    elif not (force or yes) and not typer.confirm(
        f"Refresh the wxops playbook ({', '.join(selected)}) in {folder} (owned files only)?"
    ):
        raise typer.Exit(0)

    folder.mkdir(parents=True, exist_ok=True)
    written = deleted = 0
    for p in selected:
        owned = (manifests[p] or {}).get("files", {})
        w, d, hashes = apply_bundle(folder, profile_files(all_files, p), owned)
        save_manifest(folder, p, hashes)
        written += len(w)
        deleted += len(d)
    typer.echo(
        f"Playbook v{__version__} ({', '.join(selected)}): "
        f"{written} file(s) written, {deleted} removed, in {folder}"
    )
    for p in selected:
        typer.echo(_START_HINT[p])
