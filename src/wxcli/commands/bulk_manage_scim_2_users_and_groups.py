import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.errors import handle_rest_error
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling bulk-manage-scim-2-users-and-groups.")


@app.command("create")
def create(
    org_id: str = typer.Argument(help="orgId"),
    fail_on_errors: str = typer.Option(None, "--fail-on-errors", help="(required) An integer specifying the maximum number of errors that the"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """User bulk API\n\nExample --json-body:\n  '{"schemas":["..."],"failOnErrors":0,"operations":[{"method":"...","path":"...","data":"...","bulkId":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if fail_on_errors is not None:
            body["failOnErrors"] = fail_on_errors
        _missing = [f for f in ['failOnErrors'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


