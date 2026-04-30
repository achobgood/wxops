import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-captures.")


@app.command("create")
def create(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Captures\n\nExample --json-body:\n  '{"query":{"taskIds":["..."],"orgId":"...","urlExpiration":0,"includeSegments":true,"includeVARecordings":true}}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/captures/query"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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


