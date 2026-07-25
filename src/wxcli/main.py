import typer
from datetime import datetime, timezone

from wxcli import __version__
from wxcli.auth import get_api, resolve_token, WebexApi, WebexSession
from wxcli.config import get_expires_at, get_org_id, get_org_name, save_org

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
    debug: bool = typer.Option(False, "--debug", help="Show debug output"),
):
    """Show current authenticated user and org."""
    api = get_api(debug=debug)
    me = api.session.rest_get("https://webexapis.com/v1/people/me")

    display_name = me.get("displayName", "")
    email = (me.get("emails") or ["unknown"])[0]
    org_id = me.get("orgId", "")
    typer.echo(f"User:  {display_name} ({email})")
    typer.echo(f"Org:   {org_id}")

    target_org_id = get_org_id()
    target_org_name = get_org_name()
    if target_org_id:
        # The name is absent when the org was saved from /people/me because
        # /organizations was unavailable — don't render a literal "(None)".
        suffix = f"  ({target_org_name})" if target_org_name else ""
        typer.echo(f"Target: {target_org_id}{suffix}")

    roles = me.get("roles")
    if roles:
        typer.echo(f"Roles: {', '.join(roles)}")

    expires = get_expires_at()
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires)
            now = datetime.now(timezone.utc)
            remaining = exp_dt - now
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                if hours < 2:
                    typer.echo(f"Token: expires in {hours}h {minutes}m — consider refreshing soon")
                else:
                    typer.echo(f"Token: expires in {hours}h {minutes}m")
        except ValueError:
            pass


@app.command("switch-org")
def switch_org(
    org_id: str = typer.Argument(None, help="orgId to switch to (skip interactive prompt)"),
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
        typer.echo(f"Target org set: {org_name} ({org_id})")
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
            typer.echo(f"Single-org token — target org set: {only.get('displayName')} ({only.get('id')})")
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
    typer.echo(f"\nTarget org set: {selected.get('displayName')} ({selected.get('id')})")


@app.command("clear-org")
def clear_org():
    """Clear target organization — commands will target your own org."""
    save_org(None, None)
    typer.echo("Cleared target org. Commands will now target your own organization.")


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


# Hand-coded modules. locations.py/numbers.py are no longer registered here —
# they turned out to be generator-owned on disk (regenerated byte-identical at
# the 2026-07-01 spec sync). licenses.py was the last hand-written legacy
# module, retired 2026-07-02 (S3.1) after a live-verified parity check with
# the generated twin — `licenses` is now generated and manifest-registered.
from wxcli.commands.update import app as update_app
from wxcli.commands.configure import app as configure_app
from wxcli.commands.cucm import app as cucm_app

app.add_typer(update_app, name="update")
app.add_typer(configure_app, name="configure")
app.add_typer(cucm_app, name="cucm")

from wxcli.commands.cleanup import app as cleanup_app
app.add_typer(cleanup_app, name="cleanup")

from wxcli.commands.org_health_cli import app as org_health_app
app.add_typer(org_health_app, name="org-health")

from wxcli.commands.init_playbook import init as init_command
app.command(name="init")(init_command)

# Auto-generated groups — registration manifest emitted by tools/generate_commands.py.
# Explicit registrations above/below this loop are reserved for hand-written
# seams, aliases, and the guarded dev-only fs_* block.
from importlib import import_module
from wxcli.commands._registry import GENERATED_GROUPS

_generated_apps = {}
for _module, _group in GENERATED_GROUPS:
    _generated_apps[_group] = import_module(f"wxcli.commands.{_module}").app
    app.add_typer(_generated_apps[_group], name=_group)

# Hand-written download/export mounted onto the generated converged-recordings group
from wxcli.commands import converged_recordings_export
converged_recordings_export.register(_generated_apps["converged-recordings"])

# Aliases
app.add_typer(_generated_apps["customer-assist"], name="cx-essentials")  # alias: cx-essentials → customer-assist
app.add_typer(_generated_apps["people"], name="users")  # alias: users → people (replaced hand-coded users.py)
app.add_typer(_generated_apps["licenses"], name="licenses-api")  # alias for one release: licenses-api → licenses (S3.1, 2026-07-02)

# Dev-only: Flow Store CLI (gitignored, generated from specs/webex-flow-store.json)
try:
    from wxcli.commands.fs_flows import app as fs_flows_app
    app.add_typer(fs_flows_app, name="fs-flows")
    from wxcli.commands.fs_resources import app as fs_resources_app
    app.add_typer(fs_resources_app, name="fs-resources")
    from wxcli.commands.fs_templates import app as fs_templates_app
    app.add_typer(fs_templates_app, name="fs-templates")
    from wxcli.commands.fs_tracing import app as fs_tracing_app
    app.add_typer(fs_tracing_app, name="fs-tracing")
    from wxcli.commands.fs_flows_v2 import app as fs_flows_v2_app
    app.add_typer(fs_flows_v2_app, name="fs-flows-v2")
    from wxcli.commands.fs_user_prefs import app as fs_user_prefs_app
    app.add_typer(fs_user_prefs_app, name="fs-user-prefs")
    from wxcli.commands.fs_connectors import app as fs_connectors_app
    app.add_typer(fs_connectors_app, name="fs-connectors")
    from wxcli.commands.fs_expression_test import app as fs_expression_test_app
    app.add_typer(fs_expression_test_app, name="fs-expression-test")
    from wxcli.commands.fs_flow_props import app as fs_flow_props_app
    app.add_typer(fs_flow_props_app, name="fs-flow-props")
    from wxcli.commands.fs_flow_versions import app as fs_flow_versions_app
    app.add_typer(fs_flow_versions_app, name="fs-flow-versions")
    from wxcli.commands.fs_projects import app as fs_projects_app
    app.add_typer(fs_projects_app, name="fs-projects")
except ImportError:
    pass
