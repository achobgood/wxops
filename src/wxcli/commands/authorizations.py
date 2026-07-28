import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling authorizations.")


@app.command("list", short_help="List authorizations for a user.")
def cmd_list(
    person_id: str = typer.Option(None, "--person-id", help="List authorizations for this user id."),
    person_email: str = typer.Option(None, "--person-email", help="List authorizations for this user email."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List authorizations for a user."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/authorizations"
    params = {}
    if person_id is not None:
        params["personId"] = person_id
    if person_email is not None:
        params["personEmail"] = person_email
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Application', 'applicationName'), ('Type', 'type'), ('Client ID', 'clientId')], limit=limit)



@app.command("delete", short_help="Delete authorization of org and client ID.")
def delete(
    client_id: str = typer.Option(..., "--client-id", help="The unique oAuth client id."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete authorization of org and client ID.\n\n\b\nExample: wxcli authorizations delete --client-id CLIENT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm("Delete this resource?", abort=True)
    url = f"https://webexapis.com/v1/authorizations"
    params = {}
    if client_id is not None:
        params["clientId"] = client_id
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo("Deleted.")
    else:
        emit({"status": "deleted"}, output=output, fields=fields)



@app.command("delete-authorizations", short_help="Delete authorization.")
def delete_authorizations(
    authorization_id: str = typer.Argument(help="Webex AUTHORIZATION id, from: wxcli authorizations list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete authorization.\n\n\b\nExample: wxcli authorizations delete-authorizations AUTHORIZATION_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {authorization_id}?", abort=True)
    url = f"https://webexapis.com/v1/authorizations/{authorization_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {authorization_id}")
    else:
        emit({"status": "deleted", "id": authorization_id}, output=output, fields=fields)



@app.command("show", short_help="Get expiration status for a token.")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get expiration status for a token."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/authorizations/tokenExpiry"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


