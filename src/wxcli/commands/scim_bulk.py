import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Calling scim-bulk.")


_BODY_SKELETON_CREATE = '{"schemas":["..."],"failOnErrors":0,"operations":[{"method":"...","path":"...","data":"...","bulkId":"..."}]}'

@app.command("create")
def create(
    fail_on_errors: str = typer.Option(None, "--fail-on-errors", help="(required) An integer specifying the maximum number of errors that the service provider will accept before the operation is terminated and an error response is returned."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """User bulk API\n\nExample --json-body:\n  '{"schemas":["..."],"failOnErrors":0,"operations":[{"method":"...","path":"...","data":"...","bulkId":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Bulk"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)


