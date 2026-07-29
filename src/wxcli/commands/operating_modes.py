import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling operating-modes.")


@app.command("list", short_help="Read the List of Operating Modes.")
def cmd_list(
    name: str = typer.Option(None, "--name", help="List `operating modes` whose name contains this string."),
    limit_to_location_id: str = typer.Option(None, "--limit-to-location-id", help="Location query parameter to filter the `operating modes` from that location only."),
    limit_to_org_level_enabled: str = typer.Option(None, "--limit-to-org-level-enabled", help="If true, only return `operating modes` defined at the organization level."),
    order: str = typer.Option(None, "--order", help="Sort the list of `operating modes` based on `name`, either asc, or desc."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Operating Modes."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes"
    params = {}
    if name is not None:
        params["name"] = name
    if limit_to_location_id is not None:
        params["limitToLocationId"] = limit_to_location_id
    if limit_to_org_level_enabled is not None:
        params["limitToOrgLevelEnabled"] = limit_to_org_level_enabled
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="operatingModes"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("operatingModes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Level', 'level')], limit=limit)



@app.command("show", short_help="Get Details for an Operating Mode.")
def show(
    mode_id: str = typer.Argument(help="Webex OPERATING_MODE id, from: wxcli operating-modes list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for an Operating Mode.\n\n\b\nExample: wxcli operating-modes show MODE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes/{mode_id}"
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



_BODY_SKELETON_UPDATE = '{"name":"...","sameHoursDaily":{"mondayToFriday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"saturdayToSunday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."}},"differentHoursDaily":{"sunday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"monday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"tuesday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"wednesday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"thursday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"friday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"saturday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."}},"holidays":[{"name":"...","allDayEnabled":true,"startDate":"...","endDate":"...","startTime":"...","endTime":"...","recurrence":{"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}],"callForwarding":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'

@app.command("update", short_help="Modify an Operating Mode.")
def update(
    mode_id: str = typer.Argument(help="Webex OPERATING_MODE id, from: wxcli operating-modes list"),
    name: str = typer.Option(None, "--name", help="New unique name for the `operating mode`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify an Operating Mode.\n\n\b\nExample: wxcli operating-modes update MODE_ID\n\n\b\nExample --json-body: '{"name":"...","sameHoursDaily":{"mondayToFriday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"saturdayToSunday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."}},"differentHoursDaily":{"sunday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"monday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"tuesday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"wednesday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"thursday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"friday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"saturday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."}},"holidays":[{"name":"...","allDayEnabled":true,"startDate":"...","endDate":"...","startTime":"...","endTime":"...","recurrence":{"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}],"callForwarding":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes/{mode_id}"
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
        emit({"status": "updated", "id": mode_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete an Operating Mode.")
def delete(
    mode_id: str = typer.Argument(help="Webex OPERATING_MODE id, from: wxcli operating-modes list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an Operating Mode.\n\n\b\nExample: wxcli operating-modes delete MODE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {mode_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes/{mode_id}"
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
        typer.echo(f"Deleted: {mode_id}")
    else:
        emit({"status": "deleted", "id": mode_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"name":"...","type":"SAME_HOURS_DAILY","level":"ORGANIZATION","callForwarding":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"locationId":"...","sameHoursDaily":{"mondayToFriday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"saturdayToSunday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."}},"differentHoursDaily":{"sunday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"monday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"tuesday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"wednesday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"thursday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"friday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"saturday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."}},"holidays":[{"name":"...","allDayEnabled":true,"startDate":"...","endDate":"...","startTime":"...","endTime":"...","recurrence":{"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}]}'

@app.command("create", short_help="Create an Operating Mode.")
def create(
    name: str = typer.Option(None, "--name", help="(required) Unique name for the `operating mode`."),
    type_param: str = typer.Option(None, "--type", help="(required) Choices: SAME_HOURS_DAILY, DIFFERENT_HOURS_DAILY, HOLIDAY, NONE"),
    level: str = typer.Option(None, "--level", help="(required) Choices: ORGANIZATION, LOCATION"),
    location_id: str = typer.Option(None, "--location-id", help="Unique identifier of the location. Mandatory if level is `LOCATION`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Operating Mode.\n\n\b\nExample: wxcli operating-modes create --json-body '{"name":"...","type":"SAME_HOURS_DAILY","level":"ORGANIZATION","callForwarding":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'\n\n\b\nExample --json-body: '{"name":"...","type":"SAME_HOURS_DAILY","level":"ORGANIZATION","callForwarding":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"locationId":"...","sameHoursDaily":{"mondayToFriday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"saturdayToSunday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."}},"differentHoursDaily":{"sunday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"monday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"tuesday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"wednesday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"thursday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"friday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."},"saturday":{"enabled":true,"allDayEnabled":true,"startTime":"...","endTime":"..."}},"holidays":[{"name":"...","allDayEnabled":true,"startDate":"...","endDate":"...","startTime":"...","endTime":"...","recurrence":{"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes/"
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
        if level is not None:
            body["level"] = level
        if location_id is not None:
            body["locationId"] = location_id
        _missing = [f for f in ['name', 'type', 'level'] if f not in body or body[f] is None]
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



@app.command("show-holidays", short_help="Get details for an Operating Mode Holiday.")
def show_holidays(
    mode_id: str = typer.Argument(help="Webex OPERATING_MODE id, from: wxcli operating-modes list"),
    holiday_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get details for an Operating Mode Holiday.\n\n\b\nExample: wxcli operating-modes show-holidays MODE_ID HOLIDAY_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}"
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



_BODY_SKELETON_UPDATE_HOLIDAYS = '{"name":"...","allDayEnabled":true,"startDate":"...","endDate":"...","startTime":"...","endTime":"...","recurrence":{"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}'

@app.command("update-holidays", short_help="Modify an Operating Mode Holiday.")
def update_holidays(
    mode_id: str = typer.Argument(help="Webex OPERATING_MODE id, from: wxcli operating-modes list"),
    holiday_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    name: str = typer.Option(None, "--name", help="Name of the holiday."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="Specifies if the `operating mode holiday` schedule event is enabled for the entire day. If `startTime`, and `endTime` are provided, this field is ignored."),
    start_date: str = typer.Option(None, "--start-date", help="Start date of the `operating mode holiday`."),
    end_date: str = typer.Option(None, "--end-date", help="End date of the `operating mode holiday`."),
    start_time: str = typer.Option(None, "--start-time", help="Start time for the `operating mode holiday`. Mandatory if `allDayEnabled` is not set."),
    end_time: str = typer.Option(None, "--end-time", help="End time for the `operating mode holiday`. Mandatory if `allDayEnabled` is not set."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify an Operating Mode Holiday.\n\n\b\nExample: wxcli operating-modes update-holidays MODE_ID HOLIDAY_ID\n\n\b\nExample --json-body: '{"name":"...","allDayEnabled":true,"startDate":"...","endDate":"...","startTime":"...","endTime":"...","recurrence":{"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_HOLIDAYS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}"
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
        if all_day_enabled is not None:
            body["allDayEnabled"] = all_day_enabled
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
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": holiday_id}, output=output, fields=fields)



@app.command("delete-holidays", short_help="Delete an Operating Mode Holiday.")
def delete_holidays(
    mode_id: str = typer.Argument(help="Webex OPERATING_MODE id, from: wxcli operating-modes list"),
    holiday_id: str = typer.Argument(help="Webex SCHEDULE_EVENT id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an Operating Mode Holiday.\n\n\b\nExample: wxcli operating-modes delete-holidays MODE_ID HOLIDAY_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {holiday_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}"
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
        typer.echo(f"Deleted: {holiday_id}")
    else:
        emit({"status": "deleted", "id": holiday_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_HOLIDAYS = '{"name":"...","allDayEnabled":true,"startDate":"...","endDate":"...","startTime":"...","endTime":"...","recurrence":{"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}'

@app.command("create-holidays", short_help="Create an Operating Mode Holiday.")
def create_holidays(
    mode_id: str = typer.Argument(help="Webex OPERATING_MODE id, from: wxcli operating-modes list"),
    name: str = typer.Option(None, "--name", help="(required) Name of the holiday."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="(required) Specifies if the `operating mode holiday` schedule event is enabled for the entire day. `False` if the flag is not set."),
    start_date: str = typer.Option(None, "--start-date", help="(required) Start date of the `operating mode holiday`."),
    end_date: str = typer.Option(None, "--end-date", help="(required) End date of the `operating mode holiday`."),
    start_time: str = typer.Option(None, "--start-time", help="Start time for the `operating mode holiday`. Mandatory if `allDayEnabled` is false."),
    end_time: str = typer.Option(None, "--end-time", help="End time for the `operating mode holiday`. Mandatory if `allDayEnabled` is false."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Operating Mode Holiday.\n\n\b\nExample: wxcli operating-modes create-holidays MODE_ID --name NAME --all-day-enabled --start-date START_DATE --end-date END_DATE\n\n\b\nExample --json-body: '{"name":"...","allDayEnabled":true,"startDate":"...","endDate":"...","startTime":"...","endTime":"...","recurrence":{"recurYearlyByDate":{"dayOfMonth":0,"month":"JANUARY"},"recurYearlyByDay":{"day":"SUNDAY","week":"FIRST","month":"JANUARY"}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_HOLIDAYS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/operatingModes/{mode_id}/holidays"
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
        if all_day_enabled is not None:
            body["allDayEnabled"] = all_day_enabled
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        _missing = [f for f in ['name', 'allDayEnabled', 'startDate', 'endDate'] if f not in body or body[f] is None]
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



@app.command("list-available-operating-modes", short_help="Retrieve the List of Available Operating Modes in a Location.")
def list_available_operating_modes(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve the List of Available Operating Modes in a Location.\n\n\b\nExample: wxcli operating-modes list-available-operating-modes LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/operatingModes/availableOperatingModes"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("operatingModes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-available-numbers", short_help="Get Operating Mode Call Forward Available Phone Numbers.")
def list_available_numbers(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `extension`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Operating Mode Call Forward Available Phone Numbers.\n\n\b\nExample: wxcli operating-modes list-available-numbers LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/operatingModes/callForwarding/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if owner_name is not None:
        params["ownerName"] = owner_name
    if extension is not None:
        params["extension"] = extension
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber')], limit=limit)


