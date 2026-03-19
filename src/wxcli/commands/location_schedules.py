import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling location-call-settings-schedules.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Only return schedules with the matching name."),
    type_param: str = typer.Option(None, "--type", help="Choices: businessHours, holidays"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Schedules."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if type_param is not None:
        params["type"] = type_param
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("schedules", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    type_param: str = typer.Option(..., "--type", help="Choices: businessHours, holidays"),
    name: str = typer.Option(..., "--name", help="Unique name for the schedule."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    type: str = typer.Argument(help="type"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    type: str = typer.Argument(help="type"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    name: str = typer.Option(None, "--name", help="Unique name for the schedule."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    location_id: str = typer.Argument(help="locationId"),
    type: str = typer.Argument(help="type"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Schedule."""
    if not force:
        typer.confirm(f"Delete {schedule_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {schedule_id}")



@app.command("show-events")
def show_events(
    location_id: str = typer.Argument(help="locationId"),
    type: str = typer.Argument(help="type"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Schedule Event."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}/events/{event_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-events")
def update_events(
    location_id: str = typer.Argument(help="locationId"),
    type: str = typer.Argument(help="type"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    name: str = typer.Option(None, "--name", help="Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="Start date of event."),
    end_date: str = typer.Option(None, "--end-date", help="End date of event."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of event. Mandatory if the event is not all day."),
    end_time: str = typer.Option(None, "--end-time", help="End time of event. Mandatory if the event is not all day."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="An indication of whether given event is an all-day event or"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Schedule Event."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}/events/{event_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if all_day_enabled is not None:
            body["allDayEnabled"] = all_day_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-events")
def delete_events(
    location_id: str = typer.Argument(help="locationId"),
    type: str = typer.Argument(help="type"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Schedule Event."""
    if not force:
        typer.confirm(f"Delete {event_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}/events/{event_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {event_id}")



@app.command("create-events")
def create_events(
    location_id: str = typer.Argument(help="locationId"),
    type: str = typer.Argument(help="type"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    name: str = typer.Option(..., "--name", help="Name for the event."),
    start_date: str = typer.Option(..., "--start-date", help="Start Date of Event."),
    end_date: str = typer.Option(..., "--end-date", help="End Date of Event."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of event. Mandatory if the event is not all day."),
    end_time: str = typer.Option(None, "--end-time", help="End time of event. Mandatory if the event is not all day."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="An indication of whether given event is an all-day event or"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Schedule Event."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}/events"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if all_day_enabled is not None:
            body["allDayEnabled"] = all_day_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)


