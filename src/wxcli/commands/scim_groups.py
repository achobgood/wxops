import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Calling scim-groups.")


@app.command("list", short_help="Search groups.")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="The url encoded filter. The example content is 'displayName Eq \"group1@example.com\" or displayName Eq \"group2@example.com\"'. For more filter patterns, see https://datatracker.ietf.org/doc/html/rfc7644#section-3.4.2.2. If the value is empty, the API returns all groups under the organization."),
    attributes: str = typer.Option(None, "--attributes", help="The attributes to return."),
    excluded_attributes: str = typer.Option(None, "--excluded-attributes", help="Attributes to be excluded from the return."),
    sort_by: str = typer.Option(None, "--sort-by", help="A string indicating the attribute whose value be used to order the returned responses. Now we only allow `displayName, id, meta.lastModified` to sort."),
    sort_order: str = typer.Option(None, "--sort-order", help="A string indicating the order in which the `sortBy` parameter is applied. Allowed values are `ascending` and `descending`."),
    start_index: str = typer.Option(None, "--start-index", help="An integer indicating the 1-based index of the first query result. The default is 1."),
    count: str = typer.Option(None, "--count", help="An integer indicating the desired maximum number of query results per page. The default is 100."),
    include_members: str = typer.Option(None, "--include-members", help="Default \"false\". If false, no members returned."),
    member_type: str = typer.Option(None, "--member-type", help="Filter the members by member type. Sample data: `user`, `machine`, `group`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search groups."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if excluded_attributes is not None:
        params["excludedAttributes"] = excluded_attributes
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_order is not None:
        params["sortOrder"] = sort_order
    if start_index is not None:
        params["startIndex"] = start_index
    if count is not None:
        params["count"] = count
    if include_members is not None:
        params["includeMembers"] = include_members
    if member_type is not None:
        params["memberType"] = member_type
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
    items = result.get("Resources", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('External ID', 'externalId')], limit=limit)



_BODY_SKELETON_CREATE = '{"schemas":["..."],"displayName":"...","externalId":"...","members":[{"value":"...","type":"..."}],"urn:scim:schemas:extension:cisco:webexidentity:2.0:Group":{"usage":"...","owners":[{"value":"..."}],"managedBy":[{"orgId":"...","type":"...","id":"...","role":"..."}]}}'

@app.command("create", short_help="Create a group.")
def create(
    display_name: str = typer.Option(None, "--display-name", help="(required) A human-readable name for the Group."),
    external_id: str = typer.Option(None, "--external-id", help="An identifier for the resource as defined by the provisioning client."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a group.\n\n\b\nExample: wxcli scim-groups create --json-body '{"schemas":["..."],"displayName":"..."}'\n\n\b\nExample --json-body: '{"schemas":["..."],"displayName":"...","externalId":"...","members":[{"value":"...","type":"..."}],"urn:scim:schemas:extension:cisco:webexidentity:2.0:Group":{"usage":"...","owners":[{"value":"..."}],"managedBy":[{"orgId":"...","type":"...","id":"...","role":"..."}]}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups"
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



@app.command("show", short_help="Get a group.")
def show(
    group_id: str = typer.Argument(help="UUID, from: wxcli scim-groups list"),
    excluded_attributes: str = typer.Option(None, "--excluded-attributes", help="Attributes to be excluded from the return."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a group.\n\n\b\nExample: wxcli scim-groups show GROUP_ID"""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups/{group_id}"
    params = {}
    if excluded_attributes is not None:
        params["excludedAttributes"] = excluded_attributes
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"schemas":["..."],"displayName":"...","externalId":"...","members":[{"value":"...","type":"..."}],"urn:scim:schemas:extension:cisco:webexidentity:2.0:Group":{"usage":"...","owners":[{"value":"..."}],"managedBy":[{"orgId":"...","type":"...","id":"...","role":"..."}]}}'

@app.command("update", short_help="Update a group with PUT.")
def update(
    group_id: str = typer.Argument(help="UUID, from: wxcli scim-groups list"),
    display_name: str = typer.Option(None, "--display-name", help="A human-readable name for the group."),
    external_id: str = typer.Option(None, "--external-id", help="An identifier for the resource as defined by the provisioning client."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a group with PUT.\n\n\b\nExample: wxcli scim-groups update GROUP_ID --json-body '{"schemas":["..."],"displayName":"..."}'\n\n\b\nExample --json-body: '{"schemas":["..."],"displayName":"...","externalId":"...","members":[{"value":"...","type":"..."}],"urn:scim:schemas:extension:cisco:webexidentity:2.0:Group":{"usage":"...","owners":[{"value":"..."}],"managedBy":[{"orgId":"...","type":"...","id":"...","role":"..."}]}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups/{group_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if display_name is not None:
            body["displayName"] = display_name
        if external_id is not None:
            body["externalId"] = external_id
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
        emit({"status": "updated", "id": group_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_GROUPS = '{"schemas":["..."],"Operations":[{"op":"add","path":"...","value":"..."}]}'

@app.command("update-groups", short_help="Update a group with PATCH.")
def update_groups(
    group_id: str = typer.Argument(help="UUID, from: wxcli scim-groups list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a group with PATCH.\n\n\b\nExample: wxcli scim-groups update-groups GROUP_ID --json-body '{"schemas":["..."],"Operations":[{"op":"add"}]}'\n\n\b\nExample --json-body: '{"schemas":["..."],"Operations":[{"op":"add","path":"...","value":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_GROUPS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups/{group_id}"
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



@app.command("delete", short_help="Delete a group.")
def delete(
    group_id: str = typer.Argument(help="UUID, from: wxcli scim-groups list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a group.\n\n\b\nExample: wxcli scim-groups delete GROUP_ID"""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {group_id}?", abort=True)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups/{group_id}"
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



@app.command("list-members", short_help="Get Group Members.")
def list_members(
    group_id: str = typer.Argument(help="UUID, from: wxcli scim-groups list"),
    start_index: str = typer.Option(None, "--start-index", help="The index to start for group pagination."),
    count: str = typer.Option(None, "--count", help="Non-negative integer that specifies the desired number of search results per page. The maximum value for the count is 500."),
    member_type: str = typer.Option(None, "--member-type", help="Filter the members by member type. Sample data: `user`, `machine`, `group`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Group Members.\n\n\b\nExample: wxcli scim-groups list-members GROUP_ID"""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups/{group_id}/Members"
    params = {}
    if start_index is not None:
        params["startIndex"] = start_index
    if count is not None:
        params["count"] = count
    if member_type is not None:
        params["memberType"] = member_type
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
    emit(items, output=output, fields=fields, columns=[('Type', 'type'), ('Value', 'value'), ('Display', 'display')], limit=limit)


