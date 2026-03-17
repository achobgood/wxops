import typer
from datetime import datetime, timezone

from wxcli import __version__
from wxcli.auth import get_api
from wxcli.config import get_expires_at

app = typer.Typer(
    name="wxcli",
    help="Webex Calling CLI — provision and manage Webex Calling from the terminal.",
    no_args_is_help=True,
)


def version_callback(value: bool):
    if value:
        typer.echo(f"wxcli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True),
):
    pass


@app.command()
def whoami(
    debug: bool = typer.Option(False, "--debug", help="Show debug output"),
):
    """Show current authenticated user and org."""
    api = get_api(debug=debug)
    me = api.people.me()

    typer.echo(f"User:  {me.display_name} ({me.emails[0]})")
    typer.echo(f"Org:   {me.org_id}")

    roles = getattr(me, "roles", None)
    if roles:
        typer.echo(f"Roles: {', '.join(roles)}")

    expires = get_expires_at()
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires)
            now = datetime.now(timezone.utc)
            remaining = exp_dt - now
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            if remaining.total_seconds() <= 0:
                typer.echo("Token: EXPIRED — run 'wxcli configure'", err=True)
            elif hours < 2:
                typer.echo(f"Token: expires in {hours}h {minutes}m — consider refreshing soon")
            else:
                typer.echo(f"Token: expires in {hours}h {minutes}m")
        except ValueError:
            pass


# Register sub-commands
from wxcli.commands.configure import app as configure_app
from wxcli.commands.locations import app as locations_app
from wxcli.commands.users import app as users_app
from wxcli.commands.numbers import app as numbers_app
from wxcli.commands.licenses import app as licenses_app

app.add_typer(configure_app, name="configure")
app.add_typer(locations_app, name="locations")
app.add_typer(users_app, name="users")
app.add_typer(numbers_app, name="numbers")
app.add_typer(licenses_app, name="licenses")
