import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling xapi.")


@app.command("show", short_help="Query Status.")
def show(
    device_id: str = typer.Option(..., "--device-id", help="The unique identifier for the Webex RoomOS Device."),
    name: str = typer.Option(..., "--name", help="A list of status expressions used to query the Webex RoomOS Device. See the [xAPI section of the Device Developers Guide](/docs/api/guides/device-developers-guide#xapi) for a description of status expressions. A request can contain at most 10 different status expressions."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Status.\n\n\b\nExample: wxcli xapi show --device-id DEVICE_ID --name NAME"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/xapi/status"
    params = {}
    if device_id is not None:
        params["deviceId"] = device_id
    if name is not None:
        params["name"] = name
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list", short_help="Query Schema.")
def cmd_list(
    device_id: str = typer.Option(..., "--device-id", help="A list of device IDs to query schemas from. A request can contain at most 5 device IDs."),
    status: str = typer.Option(None, "--status", help="A list of status key expressions to query schemas for. Supports patterns. Requires the `spark:xapi_statuses` scope."),
    command: str = typer.Option(None, "--command", help="A list of command key expressions to query schemas for. Supports patterns. Requires the `spark:xapi_commands` scope."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Schema.\n\n\b\nExample: wxcli xapi list --device-id DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/xapi/schema"
    params = {}
    if device_id is not None:
        params["deviceId"] = device_id
    if status is not None:
        params["status"] = status
    if command is not None:
        params["command"] = command
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Device ID', 'deviceId')], limit=limit)



_BODY_SKELETON_CREATE = '{"deviceId":"...","arguments":{"Level":0},"body":{"Booking":{"Id":"...","Title":"...","Protocol":"...","Time":"...","Organizer":"...","Number":"..."}}}'

@app.command("create", short_help="Execute Command.")
def create(
    command_name: str = typer.Argument(help="commandName"),
    device_id: str = typer.Option(None, "--device-id", help="(required) The unique identifier for the Webex RoomOS Device."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Execute Command.\n\n\b\nExample: wxcli xapi create COMMAND_NAME --device-id DEVICE_ID\n\n\b\nExample --json-body: '{"deviceId":"...","arguments":{"Level":0},"body":{"Booking":{"Id":"...","Title":"...","Protocol":"...","Time":"...","Organizer":"...","Number":"..."}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/xapi/command/{command_name}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if device_id is not None:
            body["deviceId"] = device_id
        _missing = [f for f in ['deviceId'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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


