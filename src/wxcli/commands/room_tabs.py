import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling room-tabs.")


@app.command("list", short_help="List Room Tabs.")
def cmd_list(
    room_id: str = typer.Option(..., "--room-id", help="ID of the room for which to list room tabs."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Room Tabs.\n\n\b\nExample: wxcli room-tabs list --room-id ROOM_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/tabs"
    params = {}
    if room_id is not None:
        params["roomId"] = room_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            if "max" not in params:
                params["max"] = 1000
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Room ID', 'roomId'), ('Room Type', 'roomType'), ('Content URL', 'contentUrl')], limit=limit)



_BODY_SKELETON_CREATE = '{"roomId":"...","contentUrl":"...","displayName":"..."}'

@app.command("create", short_help="Create a Room Tab.")
def create(
    room_id: str = typer.Option(None, "--room-id", help="(required) A unique identifier for the room."),
    content_url: str = typer.Option(None, "--content-url", help="(required) URL of the Room Tab. Must use `https` protocol."),
    display_name: str = typer.Option(None, "--display-name", help="(required) User-friendly name for the room tab."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Room Tab.\n\n\b\nExample: wxcli room-tabs create --room-id ROOM_ID --content-url CONTENT_URL --display-name DISPLAY_NAME\n\n\b\nExample --json-body: '{"roomId":"...","contentUrl":"...","displayName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/tabs"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if room_id is not None:
            body["roomId"] = room_id
        if content_url is not None:
            body["contentUrl"] = content_url
        if display_name is not None:
            body["displayName"] = display_name
        _missing = [f for f in ['roomId', 'contentUrl', 'displayName'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Room Tab Details.")
def show(
    id: str = typer.Argument(help="Webex MEMBERSHIP id, from: wxcli room-tabs list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Room Tab Details.\n\n\b\nExample: wxcli room-tabs show ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/tabs/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"roomId":"...","contentUrl":"...","displayName":"..."}'

@app.command("update", short_help="Update a Room Tab.")
def update(
    id: str = typer.Argument(help="Webex MEMBERSHIP id, from: wxcli room-tabs list"),
    room_id: str = typer.Option(None, "--room-id", help="ID of the room that contains the room tab in question."),
    content_url: str = typer.Option(None, "--content-url", help="Content URL of the Room Tab. URL must use `https` protocol."),
    display_name: str = typer.Option(None, "--display-name", help="User-friendly name for the room tab."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Room Tab.\n\n\b\nExample: wxcli room-tabs update ID --room-id ROOM_ID --content-url CONTENT_URL --display-name DISPLAY_NAME\n\n\b\nExample --json-body: '{"roomId":"...","contentUrl":"...","displayName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/tabs/{id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if room_id is not None:
            body["roomId"] = room_id
        if content_url is not None:
            body["contentUrl"] = content_url
        if display_name is not None:
            body["displayName"] = display_name
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Room Tab.")
def delete(
    id: str = typer.Argument(help="Webex MEMBERSHIP id, from: wxcli room-tabs list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Room Tab.\n\n\b\nExample: wxcli room-tabs delete ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/room/tabs/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)


