import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling authorizations.")


@app.command("list")
def cmd_list(
    person_id: str = typer.Option(None, "--person-id", help="List authorizations for this user id."),
    person_email: str = typer.Option(None, "--person-email", help="List authorizations for this user email."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Application', 'applicationName'), ('Type', 'type'), ('Client ID', 'clientId')], limit=limit)



@app.command("delete")
def delete(
    client_id: str = typer.Option(..., "--client-id", help="The unique oAuth client id."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete authorization of org and client ID."""
    if not force:
        typer.confirm("Delete this resource?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/authorizations"
    params = {}
    if client_id is not None:
        params["clientId"] = client_id
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo("Deleted.")



@app.command("delete-authorizations")
def delete_authorizations(
    authorization_id: str = typer.Argument(help="authorizationId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete authorization."""
    if not force:
        typer.confirm(f"Delete {authorization_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/authorizations/{authorization_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {authorization_id}")



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get expiration status for a token."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/authorizations/tokenExpiry"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)


