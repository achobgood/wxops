import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-dnc.")


_BODY_SKELETON_CREATE = '{"phoneNumber":"...","source":"...","reason":"..."}'

@app.command("create")
def create(
    dnc_list_name: str = typer.Argument(help="dncListName"),
    phone_number: str = typer.Option(None, "--phone-number", help="(required) The phone number to add to the DNC list. Must be in E.164 format (e.g., +1234567890)."),
    source: str = typer.Option(None, "--source", help="(required) The source or origin of the DNC entry. This helps track where the request originated from."),
    reason: str = typer.Option(None, "--reason", help="Optional reason for adding the phone number to the DNC list. This can help with compliance documentation."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add Phone Number to DNC List\n\nExample --json-body:\n  '{"phoneNumber":"...","source":"...","reason":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/dncList/{dnc_list_name}/phoneNumber"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if source is not None:
            body["source"] = source
        if reason is not None:
            body["reason"] = reason
        _missing = [f for f in ['phoneNumber', 'source'] if f not in body or body[f] is None]
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



@app.command("show")
def show(
    dnc_list_name: str = typer.Argument(help="dncListName"),
    phone_number: str = typer.Argument(help="phoneNumber"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Phone Number from DNC List."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/dncList/{dnc_list_name}/phoneNumber/{phone_number}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("delete")
def delete(
    dnc_list_name: str = typer.Argument(help="dncListName"),
    phone_number: str = typer.Argument(help="phoneNumber"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove Phone Number from DNC List."""
    if not force:
        typer.confirm(f"Delete {phone_number}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/dncList/{dnc_list_name}/phoneNumber/{phone_number}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {phone_number}")
    else:
        emit({"status": "removed", "id": phone_number}, output=output, fields=fields)


