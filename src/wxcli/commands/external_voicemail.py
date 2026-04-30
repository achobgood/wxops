import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling external-voicemail.")


@app.command("create")
def create(
    id_param: str = typer.Option(..., "--id", help="Unique identifier for the user or workspace."),
    action: str = typer.Option(None, "--action", help="(required) Choices: SET, CLEAR"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Set or Clear Message Waiting Indicator (MWI) Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/externalVoicemail/mwi"
    params = {}
    if id_param is not None:
        params["id"] = id_param
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if action is not None:
            body["action"] = action
        _missing = [f for f in ['action'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
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


