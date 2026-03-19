import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling room-tabs.")


@app.command("list")
def cmd_list(
    room_id: str = typer.Option(None, "--room-id", help="ID of the room for which to list room tabs."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Room Tabs."""
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
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    room_id: str = typer.Option(..., "--room-id", help="A unique identifier for the room."),
    content_url: str = typer.Option(..., "--content-url", help="URL of the Room Tab. Must use `https` protocol."),
    display_name: str = typer.Option(..., "--display-name", help="User-friendly name for the room tab."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Room Tab."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/tabs"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if room_id is not None:
            body["roomId"] = room_id
        if content_url is not None:
            body["contentUrl"] = content_url
        if display_name is not None:
            body["displayName"] = display_name
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
    else:
        print_json(result)



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Room Tab Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/tabs/{id}"
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
    id: str = typer.Argument(help="id"),
    room_id: str = typer.Option(None, "--room-id", help="ID of the room that contains the room tab in question."),
    content_url: str = typer.Option(None, "--content-url", help="Content URL of the Room Tab. URL must use `https` protocol."),
    display_name: str = typer.Option(None, "--display-name", help="User-friendly name for the room tab."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Room Tab."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/tabs/{id}"
    if json_body:
        body = json.loads(json_body)
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
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Room Tab."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/room/tabs/{id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {id}")


