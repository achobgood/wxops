import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling hot-desking-members.")


@app.command("list")
def cmd_list(
    person_id: str = typer.Argument(help="personId"),
    location_id: str = typer.Option(None, "--location-id", help="Return only available members in this location."),
    member_name: str = typer.Option(None, "--member-name", help="Search for available members by name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for available members by phone number."),
    extension: str = typer.Option(None, "--extension", help="Search for available members by extension."),
    order: str = typer.Option(None, "--order", help="Sort order for the available member list. Multiple order values may be provided."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Available Hot Desking Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/availableMembers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="members"))
    except WebexError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-members")
def list_members(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hot Desking Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/members"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update")
def update(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Hot Desking Members\n\nExample --json-body:\n  '{"members":[{"id":"...","port":"...","primaryOwner":"...","lineType":"...","lineWeight":"...","t38FaxCompressionEnabled":"...","hotlineEnabled":"...","hotlineDestination":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/members"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")


