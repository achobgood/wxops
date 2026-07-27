import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling ecm.")


@app.command("list")
def cmd_list(
    room_id: str = typer.Option(..., "--room-id", help="ID of the room for which to list the ECM folder."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List ECM folder."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/linkedFolders"
    params = {}
    if room_id is not None:
        params["roomId"] = room_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Room ID', 'roomId'), ('Room Type', 'roomType'), ('Drive ID', 'driveId')], limit=limit)



_BODY_SKELETON_CREATE = '{"roomId":"...","contentUrl":"...","displayName":"...","driveId":"...","itemId":"...","defaultFolder":"..."}'

@app.command("create")
def create(
    room_id: str = typer.Option(None, "--room-id", help="(required) A unique identifier for the room."),
    content_url: str = typer.Option(None, "--content-url", help="(required) URL of the ECM folder."),
    display_name: str = typer.Option(None, "--display-name", help="(required) This should match the folder name in the ECM backend."),
    drive_id: str = typer.Option(None, "--drive-id", help="(required) Sharepoint or OneDrive drive id. It can be queried via MS Graph APIs."),
    item_id: str = typer.Option(None, "--item-id", help="(required) Sharepoint or OneDrive item id. It can be queried via MS Graph APIs."),
    default_folder: str = typer.Option(None, "--default-folder", help="(required) Makes the folder the default storage for the space."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an ECM folder configuration\n\nExample --json-body:\n  '{"roomId":"...","contentUrl":"...","displayName":"...","driveId":"...","itemId":"...","defaultFolder":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/linkedFolders"
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
        if drive_id is not None:
            body["driveId"] = drive_id
        if item_id is not None:
            body["itemId"] = item_id
        if default_folder is not None:
            body["defaultFolder"] = default_folder
        _missing = [f for f in ['roomId', 'contentUrl', 'displayName', 'driveId', 'itemId', 'defaultFolder'] if f not in body or body[f] is None]
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



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get ECM Folder Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/linkedFolders/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"roomId":"...","contentUrl":"...","displayName":"...","driveId":"...","itemId":"...","defaultFolder":"..."}'

@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    room_id: str = typer.Option(None, "--room-id", help="ID of the room that contains the room tab in question."),
    content_url: str = typer.Option(None, "--content-url", help="Content URL of the folder."),
    display_name: str = typer.Option(None, "--display-name", help="This should match the folder name in the ECM backend."),
    drive_id: str = typer.Option(None, "--drive-id", help="Sharepoint or OneDrive drive id. It can be queried via MS Graph APIs."),
    item_id: str = typer.Option(None, "--item-id", help="Sharepoint or OneDrive item id. It can be queried via MS Graph APIs."),
    default_folder: str = typer.Option(None, "--default-folder", help="Makes the folder the default storage for the space."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an ECM Linked Folder\n\nExample --json-body:\n  '{"roomId":"...","contentUrl":"...","displayName":"...","driveId":"...","itemId":"...","defaultFolder":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/linkedFolders/{id}"
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
        if drive_id is not None:
            body["driveId"] = drive_id
        if item_id is not None:
            body["itemId"] = item_id
        if default_folder is not None:
            body["defaultFolder"] = default_folder
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



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unlink an ECM linked folder."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/linkedFolders/{id}"
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


