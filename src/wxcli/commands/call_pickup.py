import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling call-pickup.")


@app.command("list", short_help="Read the List of Call Pickups.")
def cmd_list(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    order: str = typer.Option(None, "--order", help="Sort the list of call pickups by name, either ASC or DSC. Default is ASC."),
    name: str = typer.Option(None, "--name", help="Return the list of call pickups that contains the given name. The maximum length is 80."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Pickups.\n\n\b\nExample: wxcli call-pickup list LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callPickups"
    params = {}
    if order is not None:
        params["order"] = order
    if name is not None:
        params["name"] = name
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
    items = result.get("callPickups", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","notificationType":"NONE","notificationDelayTimerSeconds":0,"agents":["..."]}'

@app.command("create", short_help="Create a Call Pickup.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the call pickup. The maximum length is 80."),
    notification_type: str = typer.Option(None, "--notification-type", help="Choices: NONE, AUDIO_ONLY, VISUAL_ONLY, AUDIO_AND_VISUAL"),
    notification_delay_timer_seconds: str = typer.Option(None, "--notification-delay-timer-seconds", help="After the number of seconds given by the `notificationDelayTimerSeconds` has elapsed, notify every member of the call pickup group when an incoming call goes unanswered. The `notificationType` field specifies the notification method. Default: 6."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Call Pickup.\n\n\b\nExample: wxcli call-pickup create LOCATION_ID --name NAME\n\n\b\nExample --json-body: '{"name":"...","notificationType":"NONE","notificationDelayTimerSeconds":0,"agents":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callPickups"
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
        if notification_type is not None:
            body["notificationType"] = notification_type
        if notification_delay_timer_seconds is not None:
            body["notificationDelayTimerSeconds"] = notification_delay_timer_seconds
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Details for a Call Pickup.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    call_pickup_id: str = typer.Argument(help="Webex CALL_PICKUP id, from: wxcli call-pickup list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Pickup.\n\n\b\nExample: wxcli call-pickup show LOCATION_ID CALL_PICKUP_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callPickups/{call_pickup_id}"
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



_BODY_SKELETON_UPDATE = '{"name":"...","notificationType":"NONE","notificationDelayTimerSeconds":0,"agents":["..."]}'

@app.command("update", short_help="Update a Call Pickup.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    call_pickup_id: str = typer.Argument(help="Webex CALL_PICKUP id, from: wxcli call-pickup list"),
    name: str = typer.Option(None, "--name", help="Unique name for the call pickup. The maximum length is 80."),
    notification_type: str = typer.Option(None, "--notification-type", help="Choices: NONE, AUDIO_ONLY, VISUAL_ONLY, AUDIO_AND_VISUAL"),
    notification_delay_timer_seconds: str = typer.Option(None, "--notification-delay-timer-seconds", help="After the number of seconds given by the `notificationDelayTimerSeconds` has elapsed, notify every member of the call pickup group when an incoming call goes unanswered. The `notificationType` field specifies the notification method. Default: 6."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Pickup.\n\n\b\nExample: wxcli call-pickup update LOCATION_ID CALL_PICKUP_ID\n\n\b\nExample --json-body: '{"name":"...","notificationType":"NONE","notificationDelayTimerSeconds":0,"agents":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callPickups/{call_pickup_id}"
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
        if notification_type is not None:
            body["notificationType"] = notification_type
        if notification_delay_timer_seconds is not None:
            body["notificationDelayTimerSeconds"] = notification_delay_timer_seconds
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
        emit({"status": "updated", "id": call_pickup_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Call Pickup.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    call_pickup_id: str = typer.Argument(help="Webex CALL_PICKUP id, from: wxcli call-pickup list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Pickup.\n\n\b\nExample: wxcli call-pickup delete LOCATION_ID CALL_PICKUP_ID"""
    if not force:
        typer.confirm(f"Delete {call_pickup_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callPickups/{call_pickup_id}"
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
        typer.echo(f"Deleted: {call_pickup_id}")
    else:
        emit({"status": "deleted", "id": call_pickup_id}, output=output, fields=fields)



@app.command("list-available-users", short_help="Get available agents from Call Pickups.")
def list_available_users(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    call_pickup_name: str = typer.Option(None, "--call-pickup-name", help="Only return available agents from call pickups with the matching name."),
    name: str = typer.Option(None, "--name", help="Only return available agents with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return available agents with the matching primary number."),
    order: str = typer.Option(None, "--order", help="Order the available agents according to the designated fields. Up to three vertical bar (|) separated sort order fields may be specified. Available sort fields: `fname`, `lname`, `extension`, `number`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get available agents from Call Pickups.\n\n\b\nExample: wxcli call-pickup list-available-users LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callPickups/availableUsers"
    params = {}
    if call_pickup_name is not None:
        params["callPickupName"] = call_pickup_name
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("agents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Phone Number', 'phoneNumber')], limit=limit)


