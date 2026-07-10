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

app = typer.Typer(help="Materialize the bundled Claude Code playbook into a local project folder.")

MANIFEST_REL = Path(".claude") / ".wxops-manifest.json"


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


def load_manifest(folder: Path) -> dict | None:
    path = folder / MANIFEST_REL
    return json.loads(path.read_text()) if path.exists() else None


def save_manifest(folder: Path, hashes: dict[str, str]) -> None:
    path = folder / MANIFEST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"wxops_playbook": True, "version": __version__, "files": hashes}, indent=2
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


def do_uninstall(folder: Path) -> None:
    manifest = load_manifest(folder)
    if manifest is None:
        typer.echo(f"No wxops manifest in {folder} — nothing to uninstall.", err=True)
        raise typer.Exit(1)
    for rel in sorted(manifest.get("files", {})):
        target = folder / rel
        if target.exists():
            target.unlink()
        _prune_empty_dirs(target.parent, folder)
    (folder / MANIFEST_REL).unlink(missing_ok=True)
    _prune_empty_dirs((folder / MANIFEST_REL).parent, folder)
    typer.echo(f"Removed the wxops playbook from {folder}. Files you added were left in place.")


# A single @app.command() with no callback: Typer collapses the app into this
# command, so `wxcli init FOLDER --flags` parses positionals and options together.
# (A group callback would treat post-positional options as subcommand names.)
@app.command()
def init(
    folder: Path = typer.Argument(Path("wxcli-playbook"), help="Target playbook folder."),
    force: bool = typer.Option(False, "--force", help="Overwrite collisions / refresh without prompting."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove every manifest-owned file, then the manifest."),
):
    """Materialize the bundled playbook (CLAUDE.md, .claude/, docs/reference/) into FOLDER."""
    folder = folder.resolve()
    if uninstall:
        do_uninstall(folder)
        return

    bundle = bundle_root()
    if not bundle.is_dir():
        typer.echo("Bundled playbook not found in this wxcli install.", err=True)
        raise typer.Exit(1)
    bundle_files = read_bundle(bundle)
    manifest = load_manifest(folder)

    if manifest is None:
        collisions = sorted(rel for rel in bundle_files if (folder / rel).exists())
        if collisions and not force:
            typer.echo(f"{folder} already contains files the playbook would overwrite:", err=True)
            for rel in collisions:
                typer.echo(f"  {rel}", err=True)
            typer.echo("Re-run with --force to overwrite them, or choose an empty folder.", err=True)
            raise typer.Exit(1)
        owned: dict[str, str] = {}
    else:
        owned = manifest.get("files", {})
        if not (force or yes) and not typer.confirm(
            f"Refresh the wxops playbook in {folder} (owned files only)?"
        ):
            raise typer.Exit(0)

    folder.mkdir(parents=True, exist_ok=True)
    written, deleted, hashes = apply_bundle(folder, bundle_files, owned)
    save_manifest(folder, hashes)
    typer.echo(
        f"Playbook v{__version__}: {len(written)} file(s) written, "
        f"{len(deleted)} removed, in {folder}"
    )
    typer.echo(
        "Open this folder in Claude Code (start a fresh session) — "
        "skills and agents load at session start."
    )
