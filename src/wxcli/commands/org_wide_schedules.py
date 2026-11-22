import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling: org-wide-schedules.")


@app.command("list", short_help="List Organization and Location Schedules.")
def cmd_list(
    name: str = typer.Option(None, "--name", help="Filters schedules by a partial, case-insensitive name match. The value cannot be blank."),
    type_param: str = typer.Option(None, "--type", help="Choices: businessHours, holidays"),
    level: str = typer.Option(None, "--level", help="Choices: LOCATION, ORGANIZATION"),
    location_id: str = typer.Option(None, "--location-id", help="Limits results to schedules associated with this location."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Organization and Location Schedules."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules"
    params = {}
    if name is not None:
        params["name"] = name
    if type_param is not None:
        params["type"] = type_param
    if level is not None:
        params["level"] = level
    if location_id is not None:
        params["locationId"] = location_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
            result = result or {}
            items = result.get("schedules", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="schedules"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Level', 'level'), ('Location Name', 'locationName')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","type":"businessHours"}'

@app.command("create", short_help="Create an Organization-Level Schedule.")
def create(
    name: str = typer.Option(None, "--name", help="(required) Name for the organization schedule. It must contain 1 to 40 characters and must not contain slashes."),
    type_param: str = typer.Option(None, "--type", help="(required) Choices: businessHours, holidays"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Organization-Level Schedule.\n\n\b\nExample: wxcli org-wide-schedules create --name NAME --type businessHours\n\n\b\nExample --json-body: '{"name":"...","type":"businessHours"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules"
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
        if type_param is not None:
            body["type"] = type_param
        _missing = [f for f in ['name', 'type'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get an Organization Schedule.")
def show(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get an Organization Schedule.\n\n\b\nExample: wxcli org-wide-schedules show businessHours SCHEDULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}"
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



_BODY_SKELETON_UPDATE = '{"name":"..."}'

@app.command("update", short_help="Update an Organization Schedule.")
def update(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    name: str = typer.Option(None, "--name", help="New name for the schedule. It must contain 1 to 40 characters and must not contain slashes."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Organization Schedule.\n\n\b\nExample: wxcli org-wide-schedules update businessHours SCHEDULE_ID --name NAME\n\n\b\nExample --json-body: '{"name":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": schedule_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete an Organization Schedule.")
def delete(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an Organization Schedule.\n\n\b\nExample: wxcli org-wide-schedules delete businessHours SCHEDULE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {schedule_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}"
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



@app.command("list-usage", short_help="List People and Features Using a Schedule.")
def list_usage(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    location_id: str = typer.Option(None, "--location-id", help="Limits usage results to the specified location."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List People and Features Using a Schedule.\n\n\b\nExample: wxcli org-wide-schedules list-usage businessHours SCHEDULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}/usage"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
            result = result or {}
            items = result.get("usedBy", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="usedBy"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Location Name', 'locationName'), ('Location ID', 'locationId')], limit=limit)



_BODY_SKELETON_VALIDATE_NAME = '{"name":"...","type":"businessHours"}'

@app.command("validate-name", short_help="Validate an Organization Schedule Name.")
def validate_name(
    name: str = typer.Option(None, "--name", help="Schedule name to check. It must not be blank and must contain 1 to 40 characters and must not contain slashes"),
    type_param: str = typer.Option(None, "--type", help="Choices: businessHours, holidays"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate an Organization Schedule Name.\n\n\b\nExample: wxcli org-wide-schedules validate-name --name NAME --type businessHours\n\n\b\nExample --json-body: '{"name":"...","type":"businessHours"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_NAME), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules/actions/validate/invoke"
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
        if type_param is not None:
            body["type"] = type_param
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_VALIDATE_EVENT_NAME = '{"name":"..."}'

@app.command("validate-event-name", short_help="Validate an Organization Schedule Event Name.")
def validate_event_name(
    schedule_type: str = typer.Argument(help="e.g. holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    name: str = typer.Option(None, "--name", help="Event name to check. It must contain 1 to 40 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate an Organization Schedule Event Name.\n\n\b\nExample: wxcli org-wide-schedules validate-event-name holidays SCHEDULE_ID --name NAME\n\n\b\nExample --json-body: '{"name":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_EVENT_NAME), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}/events/actions/validate/invoke"
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
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-events", short_help="Get an Organization Schedule Event.")
def show_events(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    event_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get an Organization Schedule Event.\n\n\b\nExample: wxcli org-wide-schedules show-events businessHours SCHEDULE_ID EVENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
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



_BODY_SKELETON_UPDATE_EVENTS = '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurWeekly":{"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true},"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}'

@app.command("update-events", short_help="Update an Organization Schedule Event.")
def update_events(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    event_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    name: str = typer.Option(None, "--name", help="New event name. When supplied as a non-null value, it must contain 1 to 40 characters."),
    start_date: str = typer.Option(None, "--start-date", help="New start date in `yyyy-MM-dd` format."),
    end_date: str = typer.Option(None, "--end-date", help="New end date in `yyyy-MM-dd` format; when both dates are provided, it cannot precede `startDate`."),
    start_time: str = typer.Option(None, "--start-time", help="New start time in the schedule time format. When `allDayEnabled` is false, both start and end times are required."),
    end_time: str = typer.Option(None, "--end-time", help="New end time in the schedule time format. When `allDayEnabled` is false, both start and end times are required."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Organization Schedule Event.\n\n\b\nExample: wxcli org-wide-schedules update-events businessHours SCHEDULE_ID EVENT_ID\n\n\b\nExample --json-body: '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurWeekly":{"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true},"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EVENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
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
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": event_id}, output=output, fields=fields)



@app.command("delete-events", short_help="Delete an Organization Schedule Event.")
def delete_events(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    event_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an Organization Schedule Event.\n\n\b\nExample: wxcli org-wide-schedules delete-events businessHours SCHEDULE_ID EVENT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {event_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
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



_BODY_SKELETON_CREATE_EVENTS = '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":{},"recurrence":{"recurForEver":true,"recurEndDate":"..."}}'

@app.command("create-events", short_help="Create an Event in an Organization Schedule.")
def create_events(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli org-wide-schedules list"),
    schedule_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli org-wide-schedules list"),
    name: str = typer.Option(None, "--name", help="(required) Event name. Must contain 1 to 40 characters."),
    start_date: str = typer.Option(None, "--start-date", help="(required) Event start date in `yyyy-MM-dd` format."),
    end_date: str = typer.Option(None, "--end-date", help="(required) Event end date in `yyyy-MM-dd` format; cannot precede `startDate`."),
    start_time: str = typer.Option(None, "--start-time", help="Event start time. Required unless `allDayEnabled` is true; omit for all-day events."),
    end_time: str = typer.Option(None, "--end-time", help="Event end time. Required unless `allDayEnabled` is true; omit for all-day events."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Event in an Organization Schedule.\n\n\b\nExample: wxcli org-wide-schedules create-events businessHours SCHEDULE_ID --name NAME --start-date START_DATE --end-date END_DATE\n\n\b\nExample --json-body: '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":{},"recurrence":{"recurForEver":true,"recurEndDate":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_EVENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/schedules/{schedule_type}/{schedule_id}/events"
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


