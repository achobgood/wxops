import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Calling scim-groups.")


@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="The url encoded filter. The example content is 'displayName"),
    attributes: str = typer.Option(None, "--attributes", help="The attributes to return."),
    excluded_attributes: str = typer.Option(None, "--excluded-attributes", help="Attributes to be excluded from the return."),
    sort_by: str = typer.Option(None, "--sort-by", help="A string indicating the attribute whose value be used to ord"),
    sort_order: str = typer.Option(None, "--sort-order", help="A string indicating the order in which the `sortBy` paramete"),
    start_index: str = typer.Option(None, "--start-index", help="An integer indicating the 1-based index of the first query r"),
    count: str = typer.Option(None, "--count", help="An integer indicating the desired maximum number of query re"),
    include_members: str = typer.Option(None, "--include-members", help="Default \"false\". If false, no members returned."),
    member_type: str = typer.Option(None, "--member-type", help="Filter the members by member type. Sample data: `user`, `mac"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("Resources", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    display_name: str = typer.Option(None, "--display-name", help="(required) A human-readable name for the Group."),
    external_id: str = typer.Option(None, "--external-id", help="An identifier for the resource as defined by the provisionin"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a group\n\nExample --json-body:\n  '{"schemas":["..."],"displayName":"...","externalId":"...","members":[{"value":"...","type":"..."}],"urn:scim:schemas:extension:cisco:webexidentity:2.0:Group":{"usage":"...","owners":["..."],"inheritances":["..."],"managedBy":["..."]}}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show")
def show(
    group_id: str = typer.Argument(help="groupId"),
    excluded_attributes: str = typer.Option(None, "--excluded-attributes", help="Attributes to be excluded from the return."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a group."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update")
def update(
    group_id: str = typer.Argument(help="groupId"),
    display_name: str = typer.Option(None, "--display-name", help="A human-readable name for the group."),
    external_id: str = typer.Option(None, "--external-id", help="An identifier for the resource as defined by the provisionin"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a group with PUT\n\nExample --json-body:\n  '{"schemas":["..."],"displayName":"...","externalId":"...","members":[{"value":"...","type":"..."}],"urn:scim:schemas:extension:cisco:webexidentity:2.0:Group":{"usage":"...","owners":["..."],"inheritances":["..."],"managedBy":["..."]}}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups/{group_id}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("update-groups")
def update_groups(
    group_id: str = typer.Argument(help="groupId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a group with PATCH\n\nExample --json-body:\n  '{"schemas":["..."],"Operations":[{"op":"...","path":"...","value":"..."}]}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups/{group_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    group_id: str = typer.Argument(help="groupId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a group."""
    if not force:
        typer.confirm(f"Delete {group_id}?", abort=True)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Groups/{group_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {group_id}")


