import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Calling external-data-updates.")


_BODY_SKELETON_UPDATE = '{"orgId":"...","updateType":"contact","data":[{"id":"...","startTimestamp":"...","endTimestamp":"...","globalVariables":[{"name":"...","value":0}]}]}'

@app.command("update", short_help="Update Task Global Variables.")
def update(
    org_id: str = typer.Option(None, "--org-id", help="Organization identifier. It must correspond to the organization associated with the bearer token or the `X-ORGANIZATION-ID` header."),
    update_type: str = typer.Option(None, "--update-type", help="Choices: contact"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Task Global Variables.\n\n\b\nExample: wxcli external-data-updates update --json-body '{"orgId":"...","updateType":"contact","data":[{"id":"...","startTimestamp":"...","endTimestamp":"...","globalVariables":[{"name":"...","value":0}]}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v1/data/updateExternal"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if org_id is not None:
            body["orgId"] = org_id
        if update_type is not None:
            body["updateType"] = update_type
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)


