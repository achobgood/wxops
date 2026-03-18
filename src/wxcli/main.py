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

# v2: Call features
from wxcli.commands.schedules import app as schedules_app
from wxcli.commands.operating_modes import app as operating_modes_app
from wxcli.commands.auto_attendants import app as auto_attendants_app
from wxcli.commands.hunt_groups import app as hunt_groups_app
from wxcli.commands.call_queues import app as call_queues_app
from wxcli.commands.call_park import app as call_park_app
from wxcli.commands.call_pickup import app as call_pickup_app
from wxcli.commands.paging import app as paging_app
from wxcli.commands.voicemail_groups import app as voicemail_groups_app

app.add_typer(schedules_app, name="schedules")
app.add_typer(operating_modes_app, name="operating-modes")
app.add_typer(auto_attendants_app, name="auto-attendants")
app.add_typer(hunt_groups_app, name="hunt-groups")
app.add_typer(call_queues_app, name="call-queues")
app.add_typer(call_park_app, name="call-park")
app.add_typer(call_pickup_app, name="call-pickup")
app.add_typer(paging_app, name="paging")
app.add_typer(voicemail_groups_app, name="voicemail-groups")

# v3: Auto-generated from Postman collection
from wxcli.commands.call_routing import app as call_routing_app
from wxcli.commands.dect_devices_settings import app as dect_devices_app
from wxcli.commands.device_call_settings import app as device_call_settings_app
from wxcli.commands.emergency_services_settings import app as emergency_services_app
from wxcli.commands.announcement_playlist import app as announcement_playlist_app
from wxcli.commands.announcement_repository import app as announcement_repository_app
from wxcli.commands.location_call_settings import app as location_call_settings_app
from wxcli.commands.location_call_settings_call_handling import app as loc_call_handling_app
from wxcli.commands.location_call_settings_voicemail import app as loc_voicemail_app
from wxcli.commands.call_recording import app as call_recording_app
from wxcli.commands.virtual_extensions import app as virtual_extensions_app
from wxcli.commands.user_call_settings import app as user_call_settings_app
from wxcli.commands.numbers_generated import app as numbers_gen_app
from wxcli.commands.single_number_reach import app as single_number_reach_app
from wxcli.commands.call_controls import app as call_controls_app
from wxcli.commands.workspaces import app as workspaces_app
from wxcli.commands.pstn import app as pstn_app

app.add_typer(call_routing_app, name="call-routing")
app.add_typer(dect_devices_app, name="dect-devices")
app.add_typer(device_call_settings_app, name="device-settings")
app.add_typer(emergency_services_app, name="emergency-services")
app.add_typer(announcement_playlist_app, name="announcement-playlists")
app.add_typer(announcement_repository_app, name="announcements")
app.add_typer(location_call_settings_app, name="location-settings")
app.add_typer(loc_call_handling_app, name="location-call-handling")
app.add_typer(loc_voicemail_app, name="location-voicemail")
app.add_typer(call_recording_app, name="call-recording")
app.add_typer(virtual_extensions_app, name="virtual-extensions")
app.add_typer(user_call_settings_app, name="user-settings")
app.add_typer(numbers_gen_app, name="numbers-manage")
app.add_typer(single_number_reach_app, name="single-number-reach")
app.add_typer(call_controls_app, name="call-controls")
app.add_typer(workspaces_app, name="workspaces")
app.add_typer(pstn_app, name="pstn")
