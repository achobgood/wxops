import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling resource-collection.")


@app.command("create")
def create(
    orgid: str = typer.Argument(help="orgid"),
    name: str = typer.Option(None, "--name", help=""),
    version: str = typer.Option(None, "--version", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    description: str = typer.Option(None, "--description", help=""),
    resource_count: str = typer.Option(None, "--resource-count", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Resource Collection\n\nExample --json-body:\n  '{"name":"...","version":"...","organizationId":"...","resources":[{"name":"...","accessLevel":"...","ids":"..."}],"description":"...","resourceCount":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/resource-collection"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if version is not None:
            body["version"] = version
        if organization_id is not None:
            body["organizationId"] = organization_id
        if description is not None:
            body["description"] = description
        if resource_count is not None:
            body["resourceCount"] = resource_count
        if id_param is not None:
            body["id"] = id_param
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("update")
def update(
    orgid: str = typer.Argument(help="orgid"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk partial update Resource Collections\n\nExample --json-body:\n  '{"items":[{"item":"...","itemIdentifier":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/resource-collection/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create-update-resource")
def create_update_resource(
    orgid: str = typer.Argument(help="orgid"),
    resource_type: str = typer.Option(None, "--resource-type", help=""),
    resource_id: str = typer.Option(None, "--resource-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update resource with default resource collection\n\nExample --json-body:\n  '{"resourceType":"...","resourceCollections":[{"id":"..."}],"resourceId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/resource-collection/update-resource"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if resource_type is not None:
            body["resourceType"] = resource_type
        if resource_id is not None:
            body["resourceId"] = resource_id
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Resource Collection by ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/resource-collection/{id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-resource-collection")
def update_resource_collection(
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    name: str = typer.Option(None, "--name", help=""),
    version: str = typer.Option(None, "--version", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    description: str = typer.Option(None, "--description", help=""),
    resource_count: str = typer.Option(None, "--resource-count", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Resource Collection by ID\n\nExample --json-body:\n  '{"name":"...","version":"...","organizationId":"...","resources":[{"name":"...","accessLevel":"...","ids":"..."}],"description":"...","resourceCount":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/resource-collection/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if version is not None:
            body["version"] = version
        if organization_id is not None:
            body["organizationId"] = organization_id
        if description is not None:
            body["description"] = description
        if resource_count is not None:
            body["resourceCount"] = resource_count
        if id_param is not None:
            body["id"] = id_param
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Resource Collection by ID."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/resource-collection/{id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {id}")



@app.command("list")
def cmd_list(
    orgid: str = typer.Argument(help="orgid"),
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attri"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Resource Collections."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/v2/resource-collection"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if search is not None:
        params["search"] = search
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-incoming-references")
def list_incoming_references(
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific Resource Collection."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/resource-collection/{id}/incoming-references"
    params = {}
    if type_param is not None:
        params["type"] = type_param
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


