import typer
from datetime import datetime, timedelta, timezone

from wxcli.auth import WebexApi, WebexSession
from wxcli.config import DEFAULT_CONFIG_PATH, load_config, save_config, save_org
from wxcli.output import plain_mode

app = typer.Typer(help="Configure authentication.", rich_markup_mode=None if plain_mode() else "rich")


def _resolve_org(api: WebexApi) -> tuple[str | None, str | None, bool]:
    """Resolve the target org. Returns (org_id, org_name, prompted).

    A single-org token resolves to its one org without prompting; `prompted` is
    False there, and the caller saves it only when no org is configured yet.
    Resolving it at all matters because 12 operations take orgId as a *required*
    query parameter — /adminAudit/events, /admin/securityAudit/events and 9 Video
    Mesh endpoints — and the generated commands inject it from the saved config
    only. With nothing saved they fail with "Required request parameter 'orgId'
    for method parameter type String is not present".
    """
    try:
        result = api.session.rest_get("https://webexapis.com/v1/organizations")
        items = result.get("items", []) if isinstance(result, dict) else []
    except Exception:
        typer.echo("Warning: Could not list organizations. Use 'wxcli switch-org <orgId>' to set target org later.")
        return None, None, False

    if not items:
        return None, None, False

    if len(items) == 1:
        only = items[0]
        return only.get("id"), only.get("displayName"), False

    typer.echo(f"\nMultiple organizations detected:\n")
    for i, org in enumerate(items, 1):
        name = org.get("displayName", "Unknown")
        org_id = org.get("id", "")
        typer.echo(f"  {i}. {name:<30s} ({org_id})")

    typer.echo()
    choice = typer.prompt(f"Select target org [1-{len(items)}]", type=int)
    if choice < 1 or choice > len(items):
        typer.echo("Invalid selection. Use 'wxcli switch-org <orgId>' to set target org later.")
        return None, None, False

    selected = items[choice - 1]
    return selected.get("id"), selected.get("displayName"), True


@app.callback(invoke_without_command=True)
def configure():
    """Save a Webex API token for wxcli to use."""
    token = typer.prompt("Webex API token")

    typer.echo("Validating token...")
    try:
        api = WebexApi(WebexSession(token))
        me = api.session.rest_get("https://webexapis.com/v1/people/me")
    except Exception as e:
        typer.echo(f"Error: Invalid token — {e}", err=True)
        raise typer.Exit(1)

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

    # Load-then-merge: preserve existing org_id/org_name
    config = load_config()
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    existing_org = profile.get("org_id")
    profile["token"] = token
    profile["expires_at"] = expires_at
    save_config(config)

    display_name = me.get("displayName", "")
    email = (me.get("emails") or ["unknown"])[0]
    me_org_id = me.get("orgId", "")
    typer.echo(f"Authenticated: {display_name} ({email})")
    typer.echo(f"Org: {me_org_id}")

    org_id, org_name, prompted = _resolve_org(api)
    if prompted:
        save_org(org_id, org_name)
        typer.echo(f"\nTarget org set: {org_name} ({org_id})")
    elif not existing_org:
        # Nothing saved yet, and only one org is visible — save it. Without this
        # the 12 required-orgId operations fail (see _resolve_org). Fall back to
        # the org on the token if /organizations was unavailable; that value is
        # already in hand from the /people/me call above, so no extra request.
        # A previously chosen org is never overwritten here — use switch-org.
        resolved = org_id or me_org_id
        if resolved:
            save_org(resolved, org_name)

    typer.echo(f"Token saved to {DEFAULT_CONFIG_PATH}")
