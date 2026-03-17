import typer
from datetime import date, time
from typing import Optional
from wxc_sdk.common.schedules import Schedule, Event, ScheduleType
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling schedules.")


@app.command("list")
def list_schedules(
    location_id: str = typer.Argument(help="Location ID"),
    schedule_type: Optional[str] = typer.Option(None, "--type", help="Filter by type: businessHours|holidays"),
    name: Optional[str] = typer.Option(None, "--name", help="Filter by name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List schedules for a location."""
    api = get_api(debug=debug)

    kwargs = dict(obj_id=location_id)
    if schedule_type:
        kwargs["schedule_type"] = ScheduleType(schedule_type)
    if name:
        kwargs["name"] = name

    schedules = list(api.telephony.schedules.list(**kwargs))

    if output == "json":
        print_json(schedules)
    else:
        print_table(
            schedules,
            columns=[
                ("ID", "schedule_id"),
                ("Name", "name"),
                ("Type", "schedule_type"),
            ],
            limit=limit,
        )


@app.command("show")
def show_schedule(
    location_id: str = typer.Argument(help="Location ID"),
    schedule_id: str = typer.Argument(help="Schedule ID"),
    schedule_type: str = typer.Option(..., "--type", help="Schedule type: businessHours|holidays"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single schedule."""
    api = get_api(debug=debug)
    schedule = api.telephony.schedules.details(
        obj_id=location_id,
        schedule_type=ScheduleType(schedule_type),
        schedule_id=schedule_id,
    )
    print_json(schedule)


@app.command("create")
def create_schedule(
    location_id: str = typer.Argument(help="Location ID"),
    name: str = typer.Option(..., "--name", help="Schedule name"),
    schedule_type: str = typer.Option(..., "--type", help="Schedule type: businessHours|holidays"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new schedule for a location."""
    api = get_api(debug=debug)
    schedule = Schedule(
        name=name,
        schedule_type=ScheduleType(schedule_type),
    )
    schedule_id = api.telephony.schedules.create(
        obj_id=location_id,
        schedule=schedule,
    )
    typer.echo(f"Created: {schedule_id} ({name})")


@app.command("update")
def update_schedule(
    location_id: str = typer.Argument(help="Location ID"),
    schedule_id: str = typer.Argument(help="Schedule ID"),
    schedule_type: str = typer.Option(..., "--type", help="Schedule type: businessHours|holidays"),
    name: Optional[str] = typer.Option(None, "--name", help="New schedule name"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a schedule."""
    api = get_api(debug=debug)
    schedule = Schedule(
        name=name,
        new_name=name,
        schedule_type=ScheduleType(schedule_type),
    )
    api.telephony.schedules.update(
        obj_id=location_id,
        schedule=schedule,
        schedule_type=ScheduleType(schedule_type),
        schedule_id=schedule_id,
    )
    typer.echo(f"Updated: {schedule_id}")


@app.command("delete")
def delete_schedule(
    location_id: str = typer.Argument(help="Location ID"),
    schedule_id: str = typer.Argument(help="Schedule ID"),
    schedule_type: str = typer.Option(..., "--type", help="Schedule type: businessHours|holidays"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a schedule."""
    api = get_api(debug=debug)

    if not force:
        typer.confirm(f"Delete schedule {schedule_id}?", abort=True)

    api.telephony.schedules.delete_schedule(
        obj_id=location_id,
        schedule_type=ScheduleType(schedule_type),
        schedule_id=schedule_id,
    )
    typer.echo(f"Deleted: {schedule_id}")


@app.command("add-event")
def add_event(
    location_id: str = typer.Argument(help="Location ID"),
    schedule_id: str = typer.Argument(help="Schedule ID"),
    schedule_type: str = typer.Option(..., "--type", help="Schedule type: businessHours|holidays"),
    name: str = typer.Option(..., "--name", help="Event name"),
    start_date: str = typer.Option(..., "--start-date", help="Start date YYYY-MM-DD"),
    end_date: str = typer.Option(..., "--end-date", help="End date YYYY-MM-DD"),
    start_time: Optional[str] = typer.Option(None, "--start-time", help="Start time HH:MM:SS"),
    end_time: Optional[str] = typer.Option(None, "--end-time", help="End time HH:MM:SS"),
    all_day: bool = typer.Option(False, "--all-day", help="All day event"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add an event to a schedule."""
    api = get_api(debug=debug)

    event_kwargs = dict(
        name=name,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        all_day_enabled=all_day,
    )
    if start_time:
        event_kwargs["start_time"] = time.fromisoformat(start_time)
    if end_time:
        event_kwargs["end_time"] = time.fromisoformat(end_time)

    event = Event(**event_kwargs)
    event_id = api.telephony.schedules.event_create(
        obj_id=location_id,
        schedule_type=ScheduleType(schedule_type),
        schedule_id=schedule_id,
        event=event,
    )
    typer.echo(f"Created event: {event_id} ({name})")


@app.command("show-event")
def show_event(
    location_id: str = typer.Argument(help="Location ID"),
    schedule_id: str = typer.Argument(help="Schedule ID"),
    event_id: str = typer.Argument(help="Event ID"),
    schedule_type: str = typer.Option(..., "--type", help="Schedule type: businessHours|holidays"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single schedule event."""
    api = get_api(debug=debug)
    event = api.telephony.schedules.event_details(
        obj_id=location_id,
        schedule_type=ScheduleType(schedule_type),
        schedule_id=schedule_id,
        event_id=event_id,
    )
    print_json(event)


@app.command("delete-event")
def delete_event(
    location_id: str = typer.Argument(help="Location ID"),
    schedule_id: str = typer.Argument(help="Schedule ID"),
    event_id: str = typer.Argument(help="Event ID"),
    schedule_type: str = typer.Option(..., "--type", help="Schedule type: businessHours|holidays"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an event from a schedule."""
    api = get_api(debug=debug)

    if not force:
        typer.confirm(f"Delete event {event_id}?", abort=True)

    api.telephony.schedules.event_delete(
        obj_id=location_id,
        schedule_type=ScheduleType(schedule_type),
        schedule_id=schedule_id,
        event_id=event_id,
    )
    typer.echo(f"Deleted event: {event_id}")
