import subprocess
import sys
import typer
from pathlib import Path

app = typer.Typer(help="Update wxcli to the latest version.")

REPO_ROOT = Path(__file__).parent.parent.parent.parent


@app.callback(invoke_without_command=True)
def update(ctx: typer.Context):
    """Pull the latest changes from origin/main and reinstall."""
    if ctx.invoked_subcommand:
        return

    typer.echo(f"Updating from {REPO_ROOT} ...")

    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    typer.echo(result.stdout.strip() or result.stderr.strip())
    if result.returncode != 0:
        typer.echo("git pull failed.", err=True)
        raise typer.Exit(1)

    typer.echo("Reinstalling dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        typer.echo(result.stderr.strip(), err=True)
        typer.echo("pip install failed.", err=True)
        raise typer.Exit(1)

    typer.echo("Done. wxcli is up to date.")
