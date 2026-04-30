import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-session-types.")


@app.command("list")
def cmd_list(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. If siteUrl is not specified,"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Site Session Types."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/sessionTypes"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type')], limit=limit)



@app.command("list-session-types")
def list_session_types(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query."),
    person_id: str = typer.Option(None, "--person-id", help="A unique identifier for the user."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List User Session Type."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/userconfig/sessionTypes"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    if person_id is not None:
        params["personId"] = person_id
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type')], limit=limit)



@app.command("update")
def update(
    site_url: str = typer.Option(None, "--site-url", help="Site URL for the session type."),
    person_id: str = typer.Option(None, "--person-id", help="A unique identifier for the user."),
    email: str = typer.Option(None, "--email", help="The email of the user."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User Session Types\n\nExample --json-body:\n  '{"siteUrl":"...","sessionTypeIds":["..."],"personId":"...","email":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/userconfig/sessionTypes"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
        if person_id is not None:
            body["personId"] = person_id
        if email is not None:
            body["email"] = email
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")


