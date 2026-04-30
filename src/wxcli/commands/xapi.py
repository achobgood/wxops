import json
import typer
from wxcli.errors import WebexError, handle_rest_error
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
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("create")
def create(
    command_name: str = typer.Argument(help="commandName"),
    device_id: str = typer.Option(None, "--device-id", help="(required) The unique identifier for the Webex RoomOS Device."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Execute Command\n\nExample --json-body:\n  '{"deviceId":"...","arguments":{"Level":0},"body":{"Booking":{"Id":"...","Title":"...","Protocol":"...","Time":"...","Organizer":"...","Number":"..."}}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/xapi/command/{command_name}"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


