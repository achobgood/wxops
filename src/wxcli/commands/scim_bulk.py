import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Calling scim-bulk.")


@app.command("create")
def create(
    fail_on_errors: str = typer.Option(None, "--fail-on-errors", help="(required) An integer specifying the maximum number of errors that the"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """User bulk API\n\nExample --json-body:\n  '{"schemas":["..."],"failOnErrors":0,"operations":[{"method":"...","path":"...","data":"...","bulkId":"..."}]}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
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


