import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling bulk-manage-scim-2-users-and-groups.")


@app.command("create")
def create(
    org_id: str = typer.Argument(help="orgId"),
    fail_on_errors: str = typer.Option(..., "--fail-on-errors", help="An integer specifying the maximum number of errors that the"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """User bulk API."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if fail_on_errors is not None:
            body["failOnErrors"] = fail_on_errors
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


