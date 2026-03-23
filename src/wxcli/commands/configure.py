import typer
from datetime import datetime, timedelta, timezone

from wxc_sdk import WebexSimpleApi

from wxcli.config import DEFAULT_CONFIG_PATH, load_config, save_config, save_org

app = typer.Typer(help="Configure authentication.")


def _detect_and_select_org(api: WebexSimpleApi) -> tuple[str | None, str | None]:
    """Detect multi-org token and prompt for org selection. Returns (org_id, org_name)."""
    try:
        result = api.session.rest_get("https://webexapis.com/v1/organizations")
        items = result.get("items", []) if isinstance(result, dict) else []
    except Exception:
        typer.echo("Warning: Could not list organizations. Use 'wxcli switch-org' to set target org later.")
        return None, None

    if len(items) <= 1:
        return None, None

    typer.echo(f"\nMultiple organizations detected:\n")
    for i, org in enumerate(items, 1):
        name = org.get("displayName", "Unknown")
        org_id = org.get("id", "")
        typer.echo(f"  {i}. {name:<30s} ({org_id})")

    typer.echo()
    choice = typer.prompt(f"Select target org [1-{len(items)}]", type=int)
    if choice < 1 or choice > len(items):
        typer.echo("Invalid selection. Use 'wxcli switch-org' to set target org later.")
        return None, None

    selected = items[choice - 1]
    return selected.get("id"), selected.get("displayName")


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

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

    # Load-then-merge: preserve existing org_id/org_name
    config = load_config()
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    profile["token"] = token
    profile["expires_at"] = expires_at
    save_config(config)

    typer.echo(f"Authenticated: {me.display_name} ({me.emails[0]})")
    typer.echo(f"Org: {me.org_id}")

    # Multi-org detection
    org_id, org_name = _detect_and_select_org(api)
    if org_id:
        save_org(org_id, org_name)
        typer.echo(f"\nTarget org set: {org_name} ({org_id})")

    typer.echo(f"Token saved to {DEFAULT_CONFIG_PATH}")
