import typer
from datetime import date as date_type
from wxc_sdk.telephony.operating_modes import (
    OperatingMode, OperatingModeHoliday, OperatingModeSchedule,
    SameHoursDaily, DaySchedule,
)
from wxc_sdk.common.schedules import ScheduleLevel

from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling operating modes.")


@app.command("list")
def list_operating_modes(
    location_id: str = typer.Option(None, "--location", help="Filter to a specific location ID"),
    name: str = typer.Option(None, "--name", help="Filter by name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List operating modes in the organization."""
    api = get_api(debug=debug)
    modes = list(api.telephony.operating_modes.list(
        limit_to_location_id=location_id,
        name=name,
    ))
    if output == "json":
        print_json(modes)
    else:
        print_table(
            modes,
            columns=[
                ("ID", "id"),
                ("Name", "name"),
                ("Type", "type"),
            ],
            limit=limit,
        )


@app.command("show")
def show_operating_mode(
    mode_id: str = typer.Argument(help="Operating mode ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single operating mode."""
    api = get_api(debug=debug)
    mode = api.telephony.operating_modes.details(mode_id=mode_id)
    print_json(mode)


@app.command("create")
def create_operating_mode(
    name: str = typer.Option(..., "--name", help="Operating mode name"),
    mode_type: str = typer.Option(..., "--type", help="sameHoursDaily|differentHoursDaily"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new org-level operating mode."""
    api = get_api(debug=debug)
    schedule_type = OperatingModeSchedule(mode_type)
    kwargs = dict(name=name, type=schedule_type, level=ScheduleLevel.organization)
    if schedule_type == OperatingModeSchedule.same_hours_daily:
        kwargs["same_hours_daily"] = SameHoursDaily(
            monday_to_friday=DaySchedule(enabled=True, all_day_enabled=True),
            saturday_to_sunday=DaySchedule(enabled=False),
        )
    settings = OperatingMode(**kwargs)
    mode_id = api.telephony.operating_modes.create(settings=settings)
    typer.echo(f"Created: {mode_id} ({name})")


@app.command("update")
def update_operating_mode(
    mode_id: str = typer.Argument(help="Operating mode ID"),
    name: str = typer.Option(None, "--name", help="New name"),
    mode_type: str = typer.Option(None, "--type", help="sameHoursDaily|differentHoursDaily"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an existing operating mode."""
    api = get_api(debug=debug)
    mode = api.telephony.operating_modes.details(mode_id=mode_id)
    if name:
        mode.name = name
    if mode_type:
        mode.type = mode_type
    api.telephony.operating_modes.update(mode_id=mode_id, settings=mode)
    typer.echo(f"Updated: {mode_id}")


@app.command("available")
def available_operating_modes(
    location_id: str = typer.Argument(help="Location ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List operating modes available for a location."""
    api = get_api(debug=debug)
    modes = api.telephony.operating_modes.available_operating_modes(location_id=location_id)
    if output == "json":
        print_json(modes)
    else:
        print_table(
            modes,
            columns=[
                ("ID", "id"),
                ("Name", "name"),
            ],
            limit=limit,
        )


@app.command("add-holiday")
def add_holiday(
    mode_id: str = typer.Argument(help="Operating mode ID"),
    name: str = typer.Option(..., "--name", help="Holiday name"),
    start_date: str = typer.Option(..., "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD), defaults to start date"),
    all_day: bool = typer.Option(True, "--all-day/--no-all-day", help="All day event"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a holiday to an operating mode."""
    api = get_api(debug=debug)
    end = end_date or start_date
    settings = OperatingModeHoliday(
        name=name,
        start_date=date_type.fromisoformat(start_date),
        end_date=date_type.fromisoformat(end),
        all_day_enabled=all_day,
    )
    holiday_id = api.telephony.operating_modes.holiday_create(mode_id=mode_id, settings=settings)
    typer.echo(f"Created holiday: {holiday_id} ({name})")


@app.command("delete-holiday")
def delete_holiday(
    mode_id: str = typer.Argument(help="Operating mode ID"),
    holiday_id: str = typer.Argument(help="Holiday ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a holiday from an operating mode."""
    if not force:
        typer.confirm(f"Delete holiday {holiday_id} from mode {mode_id}?", abort=True)
    api = get_api(debug=debug)
    api.telephony.operating_modes.holiday_delete(mode_id=mode_id, holiday_id=holiday_id)
    typer.echo(f"Deleted holiday: {holiday_id}")
