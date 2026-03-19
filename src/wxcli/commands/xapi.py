import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling xapi.")


@app.command("show")
def show(
    device_id: str = typer.Option(..., "--device-id", help="The unique identifier for the Webex RoomOS Device."),
    name: str = typer.Option(..., "--name", help="A list of status expressions used to query the Webex RoomOS"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/xapi/status"
    params = {}
    if device_id is not None:
        params["deviceId"] = device_id
    if name is not None:
        params["name"] = name
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("create")
def create(
    command_name: str = typer.Argument(help="commandName"),
    device_id: str = typer.Option(..., "--device-id", help="The unique identifier for the Webex RoomOS Device."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Execute Command."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/xapi/command/{command_name}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if device_id is not None:
            body["deviceId"] = device_id
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


