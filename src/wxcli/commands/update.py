"""wxcli update — PyPI-based in-place upgrade (git-pull retired for managed installs)."""

import json
import os
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import httpx
import typer
from packaging.version import InvalidVersion, Version

from wxcli import __version__

app = typer.Typer(help="Update wxcli to the latest version.")

PACKAGE = "wxcli"
PYPI_DEFAULT_INDEX = "https://pypi.org"
RELEASES_URL = "https://github.com/achobgood/wxops/releases/tag"
REPO_ROOT = Path(__file__).parent.parent.parent.parent


def index_base() -> str:
    """PyPI JSON/index base — env override or public PyPI, trailing slash stripped."""
    return os.environ.get("WXCLI_UPDATE_INDEX_URL", PYPI_DEFAULT_INDEX).rstrip("/")


def index_overridden() -> bool:
    return bool(os.environ.get("WXCLI_UPDATE_INDEX_URL"))


def _read_direct_url() -> str | None:
    """Return the PEP 610 direct_url.json contents for this install, or None."""
    try:
        return metadata.distribution(PACKAGE).read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return None


_UNSET = object()  # sentinel: distinguishes "resolve live" from an explicit None


def detect_install_method(
    direct_url: str | None = _UNSET,  # type: ignore[assignment]
    prefix: str | None = None,
    in_git_worktree: bool | None = None,
) -> str:
    """Classify how wxcli is installed: 'editable', 'pipx', or 'pip'.

    All args are injectable for testing; when omitted they resolve from the
    live env. An explicit direct_url=None means "no direct_url.json" (a plain
    index install), so it must NOT fall back to the live lookup.
    """
    if direct_url is _UNSET:
        direct_url = _read_direct_url()
    if prefix is None:
        prefix = sys.prefix
    if in_git_worktree is None:
        in_git_worktree = (REPO_ROOT / ".git").exists()

    # Editable / source install — PEP 610 dir_info.editable, or a git work tree fallback.
    if direct_url:
        try:
            info = json.loads(direct_url)
        except json.JSONDecodeError:
            info = {}
        if info.get("dir_info", {}).get("editable"):
            return "editable"
    elif in_git_worktree:
        return "editable"

    # pipx install — venv lives under pipx/venvs/wxcli.
    if "pipx/venvs/wxcli" in prefix.replace("\\", "/"):
        return "pipx"

    return "pip"


def get_latest_version(base: str) -> str:
    """Return the latest published version from the PyPI JSON API."""
    resp = httpx.get(f"{base}/pypi/{PACKAGE}/json", timeout=10, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()["info"]["version"]


def compare_versions(current: str, latest: str) -> str:
    """'behind' | 'equal' | 'ahead'. Unparseable current is treated as behind."""
    try:
        cur = Version(current)
    except InvalidVersion:
        return "behind"
    lat = Version(latest)
    if cur < lat:
        return "behind"
    if cur == lat:
        return "equal"
    return "ahead"


def upgrade_command(method: str, base: str, overridden: bool) -> list[str]:
    """Build the subprocess argv that upgrades wxcli in place."""
    if method == "pipx":
        cmd = ["pipx", "upgrade", PACKAGE]
        if overridden:
            cmd.append(f"--pip-args=--index-url {base}/simple")
        return cmd
    # plain pip
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE]
    if overridden:
        cmd += ["--index-url", f"{base}/simple"]
    return cmd


def _print_editable_guidance() -> None:
    typer.echo("You're on a source/dev install.")
    typer.echo("  • Developers: update with 'git pull' in the repo.")
    typer.echo("  • To switch to a managed PyPI install: 'wxcli update --migrate'.")


def _do_migrate() -> None:
    """Cut a legacy editable clone over to a pipx-managed install."""
    if shutil.which("pipx") is None:
        typer.echo(
            "pipx is required for --migrate. Install it with:\n"
            "  python -m pip install --user pipx && python -m pipx ensurepath\n"
            "then re-run 'wxcli update --migrate'.",
        )
        raise typer.Exit(1)

    base, overridden = index_base(), index_overridden()
    install = ["pipx", "install", PACKAGE]
    if overridden:
        install.append(f"--pip-args=--index-url {base}/simple")

    typer.echo("Installing wxcli via pipx ...")
    if subprocess.run(install).returncode != 0:
        typer.echo("pipx install failed.", err=True)
        raise typer.Exit(1)

    typer.echo("Removing the old editable install ...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", PACKAGE])

    typer.echo(f"Done. The old clone at {REPO_ROOT} is safe to delete.")


def refresh_playbook(latest: str, yes: bool, cwd: Path | None = None,
                     run=subprocess.run) -> None:
    """Post-upgrade playbook refresh (spec §4.7).

    Exec the freshly-installed `wxcli init --force` in a NEW process — this
    process still holds the pre-upgrade _playbook/ package data. Windows note:
    pipx can fail to swap a running console script; the user re-runs
    `wxcli init --force` manually (documented, not solved).
    """
    folder = (cwd or Path.cwd()).resolve()
    if not (folder / ".claude" / ".wxops-manifest.json").exists():
        typer.echo(
            f"To refresh a playbook folder: run 'wxcli init --force' in it "
            f"(brings it to v{latest})."
        )
        return
    if not yes and not typer.confirm(
        f"This folder holds a wxops playbook. Refresh it to v{latest}?", default=True
    ):
        return
    if run(["wxcli", "init", "--force", str(folder)]).returncode != 0:
        typer.echo("Playbook refresh failed — run 'wxcli init --force' manually.", err=True)


@app.callback(invoke_without_command=True)
def update(
    ctx: typer.Context,
    check: bool = typer.Option(False, "--check", help="Report only; never upgrade."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
    migrate: bool = typer.Option(
        False, "--migrate", help="Switch a source/clone install to a managed pipx install."
    ),
):
    """Check PyPI for a newer wxcli and upgrade in place."""
    if ctx.invoked_subcommand:
        return

    if migrate:
        _do_migrate()
        return

    method = detect_install_method()
    if method == "editable":
        _print_editable_guidance()
        return

    base = index_base()
    try:
        latest = get_latest_version(base)
    except httpx.HTTPError as exc:
        typer.echo(f"Could not reach PyPI ({base}): {exc}", err=True)
        raise typer.Exit(1)

    status = compare_versions(__version__, latest)
    if status in ("equal", "ahead"):
        typer.echo(f"wxcli {__version__} is already the latest.")
        return

    typer.echo(f"Update available: {__version__} -> {latest}")
    typer.echo(f"Release notes: {RELEASES_URL}/v{latest}")
    if check:
        return

    if not yes and not typer.confirm("Upgrade now?"):
        raise typer.Exit(0)

    cmd = upgrade_command(method, base, index_overridden())
    if subprocess.run(cmd).returncode != 0:
        typer.echo("Upgrade failed.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Upgraded to {latest}.")
    refresh_playbook(latest, yes)
