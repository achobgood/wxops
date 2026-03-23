import typer
from datetime import datetime, timedelta, timezone

from wxc_sdk import WebexSimpleApi

from wxcli.config import DEFAULT_CONFIG_PATH, load_config, save_config

app = typer.Typer(help="Configure authentication.")


@app.callback(invoke_without_command=True)
def configure():
    """Save a Webex API token for wxcli to use."""
    token = typer.prompt("Webex API token")

    typer.echo("Validating token...")
    try:
        api = WebexSimpleApi(tokens=token)
        me = api.people.me()
    except Exception as e:
        typer.echo(f"Error: Invalid token — {e}", err=True)
        raise typer.Exit(1)

    # Dev tokens expire in 12 hours
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

    config = load_config()
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    profile["token"] = token
    profile["expires_at"] = expires_at
    save_config(config)

    typer.echo(f"Authenticated: {me.display_name} ({me.emails[0]})")
    typer.echo(f"Org: {me.org_id}")
    typer.echo(f"Token saved to {DEFAULT_CONFIG_PATH}")
