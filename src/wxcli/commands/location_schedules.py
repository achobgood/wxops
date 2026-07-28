import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling location-schedules.")


@app.command("list", short_help="Read the List of Schedules.")
def cmd_list(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="Only return schedules with the matching name."),
    type_param: str = typer.Option(None, "--type", help="Choices: businessHours, holidays"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Schedules.\n\n\b\nExample: wxcli location-schedules list LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules"
    params = {}
    if name is not None:
        params["name"] = name
    if type_param is not None:
        params["type"] = type_param
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("schedules", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="schedules"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Location Name', 'locationName'), ('Location ID', 'locationId')], limit=limit)



_BODY_SKELETON_CREATE = '{"type":"businessHours","name":"...","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":"...","recurrence":"..."}]}'

@app.command("create", short_help="Create a Schedule.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    type_param: str = typer.Option(None, "--type", help="(required) Choices: businessHours, holidays"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the schedule."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Schedule.\n\n\b\nExample: wxcli location-schedules create LOCATION_ID --type businessHours --name NAME\n\n\b\nExample --json-body: '{"type":"businessHours","name":"...","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":"...","recurrence":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
        if name is not None:
            body["name"] = name
        _missing = [f for f in ['type', 'name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("show", short_help="Get Details for a Schedule.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli location-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-schedules list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Schedule.\n\n\b\nExample: wxcli location-schedules show LOCATION_ID businessHours SCHEDULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","events":[{"name":"...","newName":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":"...","recurrence":"..."}]}'

@app.command("update", short_help="Update a Schedule.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli location-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-schedules list"),
    name: str = typer.Option(None, "--name", help="Unique name for the schedule."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Schedule.\n\n\b\nExample: wxcli location-schedules update LOCATION_ID businessHours SCHEDULE_ID --name NAME\n\n\b\nExample --json-body: '{"name":"...","events":[{"name":"...","newName":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":"...","recurrence":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": schedule_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Schedule.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli location-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-schedules list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Schedule.\n\n\b\nExample: wxcli location-schedules delete LOCATION_ID businessHours SCHEDULE_ID"""
    if not force:
        typer.confirm(f"Delete {schedule_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {schedule_id}")
    else:
        emit({"status": "deleted", "id": schedule_id}, output=output, fields=fields)



@app.command("show-events", short_help="Get Details for a Schedule Event.")
def show_events(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli location-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-schedules list"),
    event_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Schedule Event.\n\n\b\nExample: wxcli location-schedules show-events LOCATION_ID businessHours SCHEDULE_ID EVENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}/events/{event_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_EVENTS = '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."},"recurYearlyByDate":{"dayOfMonth":"...","month":"..."},"recurYearlyByDay":{"day":"...","week":"...","month":"..."}}}'

@app.command("update-events", short_help="Update a Schedule Event.")
def update_events(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    type: str = typer.Argument(help="e.g. businessHours, from: wxcli location-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-schedules list"),
    event_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    name: str = typer.Option(None, "--name", help="Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="Start date of event."),
    end_date: str = typer.Option(None, "--end-date", help="End date of event."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of event. Mandatory if the event is not all day."),
    end_time: str = typer.Option(None, "--end-time", help="End time of event. Mandatory if the event is not all day."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="An indication of whether given event is an all-day event or not. Mandatory if the `startTime` and `endTime` are not defined."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Schedule Event.\n\n\b\nExample: wxcli location-schedules update-events LOCATION_ID businessHours SCHEDULE_ID EVENT_ID --name NAME --start-date START_DATE --end-date END_DATE\n\n\b\nExample --json-body: '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."},"recurYearlyByDate":{"dayOfMonth":"...","month":"..."},"recurYearlyByDay":{"day":"...","week":"...","month":"..."}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EVENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}/events/{event_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": event_id}, output=output, fields=fields)



@app.command("delete-events", short_help="Delete a Schedule Event.")
def delete_events(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli location-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-schedules list"),
    event_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Schedule Event.\n\n\b\nExample: wxcli location-schedules delete-events LOCATION_ID businessHours SCHEDULE_ID EVENT_ID"""
    if not force:
        typer.confirm(f"Delete {event_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}/events/{event_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {event_id}")
    else:
        emit({"status": "deleted", "id": event_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_EVENTS = '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."},"recurYearlyByDate":{"dayOfMonth":"...","month":"..."},"recurYearlyByDay":{"day":"...","week":"...","month":"..."}}}'

@app.command("create-events", short_help="Create a Schedule Event.")
def create_events(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli location-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-schedules list"),
    name: str = typer.Option(None, "--name", help="(required) Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="(required) Start Date of Event."),
    end_date: str = typer.Option(None, "--end-date", help="(required) End Date of Event."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of event. Mandatory if the event is not all day."),
    end_time: str = typer.Option(None, "--end-time", help="End time of event. Mandatory if the event is not all day."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="An indication of whether given event is an all-day event or not. Mandatory if the `startTime` and `endTime` are not defined."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Schedule Event.\n\n\b\nExample: wxcli location-schedules create-events LOCATION_ID businessHours SCHEDULE_ID --name NAME --start-date START_DATE --end-date END_DATE\n\n\b\nExample --json-body: '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."},"recurYearlyByDate":{"dayOfMonth":"...","month":"..."},"recurYearlyByDay":{"day":"...","week":"...","month":"..."}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_EVENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/schedules/{type}/{schedule_id}/events"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        _missing = [f for f in ['name', 'startDate', 'endDate'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)


