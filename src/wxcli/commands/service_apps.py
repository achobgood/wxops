import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling service-apps.")


@app.command("create")
def create(
    application_id: str = typer.Argument(help="applicationId"),
    client_id: str = typer.Option(..., "--client-id", help="The OAuth client ID of the Service App"),
    client_secret: str = typer.Option(..., "--client-secret", help="The OAuth client secret of the Service App"),
    target_org_id: str = typer.Option(..., "--target-org-id", help="The organization ID for which the token will be created"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Service App Access Token."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/applications/{application_id}/token"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if client_id is not None:
            body["clientId"] = client_id
        if client_secret is not None:
            body["clientSecret"] = client_secret
        if target_org_id is not None:
            body["targetOrgId"] = target_org_id
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


