import typer
from wxc_sdk.telephony.autoattendant import (
    AutoAttendant, AutoAttendantMenu, Greeting,
    AutoAttendantKeyConfiguration, AutoAttendantAction,
)

from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling auto attendants.")


@app.command("list")
def list_auto_attendants(
    location_id: str = typer.Option(None, "--location", help="Filter by location ID"),
    name: str = typer.Option(None, "--name", help="Filter by name"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter by phone number"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List all auto attendants in the organization."""
    api = get_api(debug=debug)
    results = list(api.telephony.auto_attendant.list(
        location_id=location_id,
        name=name,
        phone_number=phone_number,
    ))

    if output == "json":
        print_json(results)
    else:
        print_table(
            results,
            columns=[
                ("ID", "auto_attendant_id"),
                ("Name", "name"),
                ("Extension", "extension"),
                ("Phone", "phone_number"),
                ("Enabled", "enabled"),
            ],
            limit=limit,
        )


@app.command("show")
def show_auto_attendant(
    location_id: str = typer.Argument(help="Location ID"),
    auto_attendant_id: str = typer.Argument(help="Auto attendant ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single auto attendant."""
    api = get_api(debug=debug)
    aa = api.telephony.auto_attendant.details(
        location_id=location_id,
        auto_attendant_id=auto_attendant_id,
    )
    print_json(aa)


@app.command("create")
def create_auto_attendant(
    location_id: str = typer.Option(..., "--location", help="Location ID"),
    name: str = typer.Option(..., "--name", help="Auto attendant name"),
    extension: str = typer.Option(..., "--extension", help="Extension number"),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number"),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Business hours schedule name"),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Holiday schedule name"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable the auto attendant"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new auto attendant."""
    api = get_api(debug=debug)

    default_key = AutoAttendantKeyConfiguration(
        key="0",
        action=AutoAttendantAction.exit,
    )
    default_menu = AutoAttendantMenu(
        greeting=Greeting.default,
        extension_enabled=True,
        key_configurations=[default_key],
    )
    settings = AutoAttendant(
        name=name,
        extension=extension,
        enabled=enabled,
        business_hours_menu=default_menu,
        after_hours_menu=default_menu,
    )
    if phone_number:
        settings.phone_number = phone_number
    if business_schedule:
        settings.business_schedule = business_schedule
    if holiday_schedule:
        settings.holiday_schedule = holiday_schedule

    aa_id = api.telephony.auto_attendant.create(
        location_id=location_id,
        settings=settings,
    )
    typer.echo(f"Created: {aa_id} ({name})")


@app.command("update")
def update_auto_attendant(
    location_id: str = typer.Argument(help="Location ID"),
    auto_attendant_id: str = typer.Argument(help="Auto attendant ID"),
    name: str = typer.Option(None, "--name", help="New name"),
    extension: str = typer.Option(None, "--extension", help="New extension"),
    phone_number: str = typer.Option(None, "--phone-number", help="New phone number"),
    enabled: bool = typer.Option(None, "--enabled/--disabled", help="Enable or disable"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an auto attendant."""
    api = get_api(debug=debug)
    aa = api.telephony.auto_attendant.details(
        location_id=location_id,
        auto_attendant_id=auto_attendant_id,
    )
    if name is not None:
        aa.name = name
    if extension is not None:
        aa.extension = extension
    if phone_number is not None:
        aa.phone_number = phone_number
    if enabled is not None:
        aa.enabled = enabled

    api.telephony.auto_attendant.update(
        location_id=location_id,
        auto_attendant_id=auto_attendant_id,
        settings=aa,
    )
    typer.echo(f"Updated: {auto_attendant_id}")


@app.command("delete")
def delete_auto_attendant(
    location_id: str = typer.Argument(help="Location ID"),
    auto_attendant_id: str = typer.Argument(help="Auto attendant ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an auto attendant."""
    if not force:
        typer.confirm(f"Delete auto attendant {auto_attendant_id}?", abort=True)
    api = get_api(debug=debug)
    api.telephony.auto_attendant.delete_auto_attendant(
        location_id=location_id,
        auto_attendant_id=auto_attendant_id,
    )
    typer.echo(f"Deleted: {auto_attendant_id}")


@app.command("list-announcements")
def list_announcements(
    location_id: str = typer.Argument(help="Location ID"),
    auto_attendant_id: str = typer.Argument(help="Auto attendant ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List announcement files for an auto attendant."""
    api = get_api(debug=debug)
    files = api.telephony.auto_attendant.list_announcement_files(
        location_id=location_id,
        auto_attendant_id=auto_attendant_id,
    )

    if output == "json":
        print_json(files)
    else:
        print_table(
            files,
            columns=[
                ("File Name", "file_name"),
            ],
            limit=limit,
        )


@app.command("delete-announcement")
def delete_announcement(
    location_id: str = typer.Argument(help="Location ID"),
    auto_attendant_id: str = typer.Argument(help="Auto attendant ID"),
    file_name: str = typer.Argument(help="Announcement file name to delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an announcement file from an auto attendant."""
    if not force:
        typer.confirm(f"Delete announcement file '{file_name}'?", abort=True)
    api = get_api(debug=debug)
    api.telephony.auto_attendant.delete_announcement_file(
        location_id=location_id,
        auto_attendant_id=auto_attendant_id,
        file_name=file_name,
    )
    typer.echo(f"Deleted announcement: {file_name}")
