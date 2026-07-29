import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling hot-desking-members.")


@app.command("list", short_help="Search Available Hot Desking Members.")
def cmd_list(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    location_id: str = typer.Option(None, "--location-id", help="Return only available members in this location."),
    member_name: str = typer.Option(None, "--member-name", help="Search for available members by name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for available members by phone number."),
    extension: str = typer.Option(None, "--extension", help="Search for available members by extension."),
    order: str = typer.Option(None, "--order", help="Sort order for the available member list. Multiple order values may be provided."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Available Hot Desking Members.\n\n\b\nExample: wxcli hot-desking-members list PERSON_ID"""
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-members", short_help="Get Hot Desking Members.")
def list_members(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hot Desking Members.\n\n\b\nExample: wxcli hot-desking-members list-members PERSON_ID"""
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE = '{"members":[{"id":"...","port":0,"primaryOwner":true,"lineType":"HOTDESKING_GUEST","lineWeight":0,"t38FaxCompressionEnabled":true,"hotlineEnabled":true,"hotlineDestination":"...","allowCallDeclineEnabled":true,"memberType":"USER"}]}'

@app.command("update", short_help="Update Hot Desking Members.")
def update(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Hot Desking Members.\n\n\b\nExample: wxcli hot-desking-members update PERSON_ID --json-body '{"members":[{"id":"...","port":0,"primaryOwner":true,"lineType":"HOTDESKING_GUEST","lineWeight":0}]}'\n\n\b\nExample --json-body: '{"members":[{"id":"...","port":0,"primaryOwner":true,"lineType":"HOTDESKING_GUEST","lineWeight":0,"t38FaxCompressionEnabled":true,"hotlineEnabled":true,"hotlineDestination":"...","allowCallDeclineEnabled":true,"memberType":"USER"}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/members"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)


