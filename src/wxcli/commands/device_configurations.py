import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling device-configurations.")


@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Device Configurations for device."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/deviceConfigurations"
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
    op: str = typer.Option(None, "--op", help="Choices: remove, replace"),
    path: str = typer.Option(None, "--path", help="Only paths ending in `/sources/configured/value` are support"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Configurations."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/deviceConfigurations"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if op is not None:
            body["op"] = op
        if path is not None:
            body["path"] = path
    try:
        result = api.session.rest_patch(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")


