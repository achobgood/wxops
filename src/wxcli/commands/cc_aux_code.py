import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling auxiliary-code.")


@app.command("list")
def cmd_list(
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
    """List references for a specific Auxiliary Code."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code/{id}/incoming-references"
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



@app.command("list-auxiliary-code-v2")
def list_auxiliary_code_v2(
    orgid: str = typer.Argument(help="orgid"),
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    desktop_profile_filter: str = typer.Option(None, "--desktop-profile-filter", help="If set to true, the API will return only the data that the u"),
    supervised_user_id: str = typer.Option(None, "--supervised-user-id", help="User Id of the Agent whose Agent Profile associated Idle Cod"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Auxiliary Code(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/v2/auxiliary-code"
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
    if desktop_profile_filter is not None:
        params["desktopProfileFilter"] = desktop_profile_filter
    if supervised_user_id is not None:
        params["supervisedUserId"] = supervised_user_id
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



@app.command("list-bulk-export")
def list_bulk_export(
    orgid: str = typer.Argument(help="orgid"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk export Auxiliary Code(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code/bulk-export"
    params = {}
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



@app.command("list-auxiliary-code-organization")
def list_auxiliary_code_organization(
    orgid: str = typer.Argument(help="orgid"),
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Auxiliary Code(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
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



@app.command("create")
def create(
    orgid: str = typer.Argument(help="orgid"),
    work_type_id: str = typer.Option(None, "--work-type-id", help=""),
    version: str = typer.Option(None, "--version", help=""),
    burnout_inclusion: str = typer.Option(None, "--burnout-inclusion", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    name: str = typer.Option(None, "--name", help=""),
    active: str = typer.Option(None, "--active", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    is_system_code: str = typer.Option(None, "--is-system-code", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    description: str = typer.Option(None, "--description", help=""),
    default_code: str = typer.Option(None, "--default-code", help=""),
    work_type_code: str = typer.Option(None, "--work-type-code", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Auxiliary Code."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if work_type_id is not None:
            body["workTypeId"] = work_type_id
        if version is not None:
            body["version"] = version
        if burnout_inclusion is not None:
            body["burnoutInclusion"] = burnout_inclusion
        if system_default is not None:
            body["systemDefault"] = system_default
        if name is not None:
            body["name"] = name
        if active is not None:
            body["active"] = active
        if organization_id is not None:
            body["organizationId"] = organization_id
        if is_system_code is not None:
            body["isSystemCode"] = is_system_code
        if id_param is not None:
            body["id"] = id_param
        if description is not None:
            body["description"] = description
        if default_code is not None:
            body["defaultCode"] = default_code
        if work_type_code is not None:
            body["workTypeCode"] = work_type_code
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



@app.command("create-bulk")
def create_bulk(
    orgid: str = typer.Argument(help="orgid"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Auxiliary Code(s)\n\nExample --json-body:\n  '{"items":[{"item":"...","itemIdentifier":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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
    """Bulk partial update Auxiliary Code(s)\n\nExample --json-body:\n  '{"items":[{"item":"...","itemIdentifier":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code/bulk"
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



@app.command("create-purge-inactive-entities")
def create_purge_inactive_entities(
    orgid: str = typer.Argument(help="orgid"),
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge ba"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Auxiliary Code(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code/purge-inactive-entities"
    params = {}
    if next_start_id is not None:
        params["nextStartId"] = next_start_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
    """Get specific Auxiliary Code by ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code/{id}"
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



@app.command("update-auxiliary-code")
def update_auxiliary_code(
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    work_type_id: str = typer.Option(None, "--work-type-id", help=""),
    version: str = typer.Option(None, "--version", help=""),
    burnout_inclusion: str = typer.Option(None, "--burnout-inclusion", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    name: str = typer.Option(None, "--name", help=""),
    active: str = typer.Option(None, "--active", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    is_system_code: str = typer.Option(None, "--is-system-code", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    description: str = typer.Option(None, "--description", help=""),
    default_code: str = typer.Option(None, "--default-code", help=""),
    work_type_code: str = typer.Option(None, "--work-type-code", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Auxiliary Code by ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if work_type_id is not None:
            body["workTypeId"] = work_type_id
        if version is not None:
            body["version"] = version
        if burnout_inclusion is not None:
            body["burnoutInclusion"] = burnout_inclusion
        if system_default is not None:
            body["systemDefault"] = system_default
        if name is not None:
            body["name"] = name
        if active is not None:
            body["active"] = active
        if organization_id is not None:
            body["organizationId"] = organization_id
        if is_system_code is not None:
            body["isSystemCode"] = is_system_code
        if id_param is not None:
            body["id"] = id_param
        if description is not None:
            body["description"] = description
        if default_code is not None:
            body["defaultCode"] = default_code
        if work_type_code is not None:
            body["workTypeCode"] = work_type_code
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
    """Delete specific Auxiliary Code by ID."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/auxiliary-code/{id}"
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


