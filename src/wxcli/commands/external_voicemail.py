import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling external-voicemail.")


@app.command("create")
def create(
    id_param: str = typer.Option(..., "--id", help="Unique identifier for the user or workspace."),
    action: str = typer.Option(..., "--action", help="Choices: SET, CLEAR"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Set or Clear Message Waiting Indicator (MWI) Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/externalVoicemail/mwi"
    params = {}
    if id_param is not None:
        params["id"] = id_param
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if action is not None:
            body["action"] = action
    try:
        result = api.session.rest_post(url, json=body, params=params)
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


