import typer
from datetime import datetime, timezone

from wxcli import __version__
from wxcli.auth import get_api, resolve_token, WebexApi, WebexSession
from wxcli.commands._lazy import LazyTyper
from wxcli.common import emit, FIELDS_HELP
from wxcli.config import get_expires_at, get_org_id, get_org_name, save_org
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import plain_mode

# LazyTyper (not typer.Typer) — see wxcli/commands/_lazy.py. Command-group
# mounting (178 generated + 5 hand-written + 3 aliases + dev-only fs_*) is
# deferred there instead of happening eagerly at import time.
app = LazyTyper(
    name="wxcli",
    help="Webex Calling CLI — provision and manage Webex Calling from the terminal.",
    no_args_is_help=True,
    rich_markup_mode=None if plain_mode() else "rich",
)


def version_callback(value: bool):
    if value:
        typer.echo(f"wxcli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True),
    no_update_check: bool = typer.Option(
        False, "--no-update-check",
        help="Skip the once-a-day PyPI update check for this run.",
    ),
):
    # Best-effort upgrade nudge; never let it break a real command.
    try:
        from wxcli.update_check import maybe_notify_update
        maybe_notify_update(__version__, disabled=no_update_check)
    except Exception:
        pass


@app.command()
def whoami(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    fields: str = typer.Option(None, "--fields", help=FIELDS_HELP),
    debug: bool = typer.Option(False, "--debug", help="Show debug output"),
):
    """Show current authenticated user and org."""
    api = get_api(debug=debug)
    # Five tips in errors.py send the reader here — "confirm it works with:
    # wxcli whoami" — so this is the command an agent reaches for when auth is
    # already broken. Bare, it raised WebexError through Typer as a Python
    # traceback: the one screen that must stay readable when nothing else works.
    try:
        me = api.session.rest_get("https://webexapis.com/v1/people/me")
    except WebexError as e:
        handle_rest_error(e)
    except Exception as e:
        handle_network_error(e)

    display_name = me.get("displayName", "")
    email = (me.get("emails") or ["unknown"])[0]
    org_id = me.get("orgId", "")
    result = {"user": display_name, "email": email, "orgId": org_id}

    target_org_id = get_org_id()
    target_org_name = get_org_name()
    if target_org_id:
        # The name is absent when the org was saved from /people/me because
        # /organizations was unavailable — don't render a literal "(None)".
        result["targetOrgId"] = target_org_id
        if target_org_name:
            result["targetOrgName"] = target_org_name

    roles = me.get("roles")
    if roles:
        result["roles"] = ", ".join(roles)

    expires = get_expires_at()
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires)
            now = datetime.now(timezone.utc)
            remaining = exp_dt - now
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                token_str = f"{hours}h {minutes}m"
                if hours < 2:
                    token_str += " — consider refreshing soon"
                result["tokenExpiresIn"] = token_str
        except ValueError:
            pass

    emit(result, output=output, fields=fields)


@app.command("switch-org")
def switch_org(
    org_id: str = typer.Argument(None, help="orgId to switch to (skip interactive prompt)"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    fields: str = typer.Option(None, "--fields", help=FIELDS_HELP),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch target organization for partner multi-org tokens."""
    token = resolve_token()
    if not token:
        typer.echo("Error: No token found. Run 'wxcli configure' first.", err=True)
        raise typer.Exit(1)

    api = WebexApi(WebexSession(token))

    if org_id:
        # Direct switch — resolve org name
        try:
            org = api.session.rest_get(f"https://webexapis.com/v1/organizations/{org_id}")
            org_name = org.get("displayName", "Unknown")
        except Exception:
            org_name = "Unknown"
        save_org(org_id, org_name)
        emit({"orgId": org_id, "orgName": org_name}, output=output, fields=fields)
        return

    # Interactive — list orgs
    try:
        result = api.session.rest_get("https://webexapis.com/v1/organizations")
        items = result.get("items", []) if isinstance(result, dict) else []
    except Exception as e:
        typer.echo(f"Error listing organizations: {e}", err=True)
        raise typer.Exit(1)

    if len(items) <= 1:
        # There is nothing to switch *between*, but the org must still be saved:
        # 12 operations take orgId as a required query parameter and the
        # generated commands inject it from config only. Saving it here is what
        # makes this the recovery path for a config written before wxcli started
        # saving the org for single-org tokens.
        if items:
            only = items[0]
            save_org(only.get("id"), only.get("displayName"))
            emit(
                {"orgId": only.get("id"), "orgName": only.get("displayName"), "singleOrgToken": True},
                output=output, fields=fields,
            )
        else:
            typer.echo("No organizations are visible to this token.", err=True)
        return

    typer.echo(f"\nAvailable organizations:\n")
    for i, org in enumerate(items, 1):
        name = org.get("displayName", "Unknown")
        oid = org.get("id", "")
        typer.echo(f"  {i}. {name:<30s} ({oid})")

    typer.echo()
    choice = typer.prompt(f"Select target org [1-{len(items)}]", type=int)
    if choice < 1 or choice > len(items):
        typer.echo("Invalid selection.", err=True)
        raise typer.Exit(1)

    selected = items[choice - 1]
    save_org(selected.get("id"), selected.get("displayName"))
    emit({"orgId": selected.get("id"), "orgName": selected.get("displayName")}, output=output, fields=fields)


@app.command("clear-org")
def clear_org(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    fields: str = typer.Option(None, "--fields", help=FIELDS_HELP),
):
    """Clear target organization — commands will target your own org."""
    save_org(None, None)
    emit(
        {"status": "cleared", "message": "Commands will now target your own organization."},
        output=output, fields=fields,
    )


@app.command("set-cc-region")
def set_cc_region(
    region: str = typer.Argument(
        help="Contact Center region: us1, eu1, eu2, anz1, ca1, jp1, sg1"
    ),
):
    """Set the Contact Center API region for cc-* commands."""
    from wxcli.config import CC_REGIONS, save_cc_region
    if region not in CC_REGIONS:
        typer.echo(f"Error: Unknown region '{region}'. Valid: {', '.join(sorted(CC_REGIONS))}", err=True)
        raise typer.Exit(1)
    save_cc_region(region)
    typer.echo(f"CC region set: {region} ({CC_REGIONS[region]})")


from wxcli.commands.init_playbook import init as init_command
app.command(name="init")(init_command)

# Every other command group — 178 generated, 5 hand-written seams
# (update/configure/cucm/cleanup/org-health), 3 aliases, and the guarded
# dev-only fs_* block — is mounted lazily by LazyTyper (see
# wxcli/commands/_lazy.py). locations.py/numbers.py are no longer
# registered here — they turned out to be generator-owned on disk
# (regenerated byte-identical at the 2026-07-01 spec sync). licenses.py was
# the last hand-written legacy module, retired 2026-07-02 (S3.1) after a
# live-verified parity check with the generated twin — `licenses` is now
# generated and manifest-registered.
