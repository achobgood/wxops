import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling groups.")


@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Searches the group by `displayName` with an operator and a value. The available operators are `eq` (equal) and `sw` (starts with). Only `displayName` can be used to filter results."),
    attributes: str = typer.Option(None, "--attributes", help="The attributes to return."),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort the results based by group `displayName`."),
    sort_order: str = typer.Option(None, "--sort-order", help="Sort results alphabetically by group display name, in ascending or descending order."),
    include_members: str = typer.Option(None, "--include-members", help="Optionally return group members in the response. The maximum number of members returned is 500."),
    start_index: str = typer.Option(None, "--start-index", help="The index to start for group pagination."),
    count: str = typer.Option(None, "--count", help="Specifies the desired number of search results per page."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List and Search Groups."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_order is not None:
        params["sortOrder"] = sort_order
    if include_members is not None:
        params["includeMembers"] = include_members
    if start_index is not None:
        params["startIndex"] = start_index
    if count is not None:
        params["count"] = count
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
    items = result.get("groups", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Member Count', 'memberSize')], limit=limit)



_BODY_SKELETON_CREATE = '{"schemas":["..."],"displayName":"...","externalId":"...","members":[{"value":"...","type":"..."}],"urn:scim:schemas:extension:cisco:webexidentity:2.0:Group":{"usage":"...","owners":["..."],"managedBy":["..."]}}'

@app.command("create")
def create(
    display_name: str = typer.Option(None, "--display-name", help="(required) A human-readable name for the Group."),
    external_id: str = typer.Option(None, "--external-id", help="An identifier for the resource as defined by the provisioning client."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Group\n\nExample --json-body:\n  '{"schemas":["..."],"displayName":"...","externalId":"...","members":[{"value":"...","type":"..."}],"urn:scim:schemas:extension:cisco:webexidentity:2.0:Group":{"usage":"...","owners":["..."],"managedBy":["..."]}}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if display_name is not None:
            body["displayName"] = display_name
        if external_id is not None:
            body["externalId"] = external_id
        _missing = [f for f in ['displayName'] if f not in body or body[f] is None]
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
    group_id: str = typer.Argument(help="groupId"),
    include_members: str = typer.Option(None, "--include-members", help="Include the members as part of the response."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Group Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups/{group_id}"
    params = {}
    if include_members is not None:
        params["includeMembers"] = include_members
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"schemas":["..."],"Operations":[{"op":"...","path":"...","value":"..."}]}'

@app.command("update")
def update(
    group_id: str = typer.Argument(help="groupId"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Group\n\nExample --json-body:\n  '{"schemas":["..."],"Operations":[{"op":"...","path":"...","value":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups/{group_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": group_id}, output=output, fields=fields)



@app.command("delete")
def delete(
    group_id: str = typer.Argument(help="groupId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Group."""
    if not force:
        typer.confirm(f"Delete {group_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups/{group_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {group_id}")
    else:
        emit({"status": "deleted", "id": group_id}, output=output, fields=fields)



@app.command("list-members")
def list_members(
    group_id: str = typer.Argument(help="groupId"),
    start_index: str = typer.Option(None, "--start-index", help="The index to start for group pagination."),
    count: str = typer.Option(None, "--count", help="Non-negative integer that specifies the desired number of search results per page. Maximum value for the count is 500."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Group Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups/{group_id}/members"
    params = {}
    if start_index is not None:
        params["startIndex"] = start_index
    if count is not None:
        params["count"] = count
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
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Member Count', 'memberSize')], limit=limit)


