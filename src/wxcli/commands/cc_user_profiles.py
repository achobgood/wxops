import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-user-profiles.")


@app.command("list")
def cmd_list(
    id: str = typer.Argument(help="id"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific User Profile."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user-profile/{id}/incoming-references"
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
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-user-profile")
def list_user_profile(
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
    """List user profiles."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile"
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
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is require"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    name: str = typer.Option(None, "--name", help="(required) The name of the user profile."),
    description: str = typer.Option(None, "--description", help="An optional description of the profile."),
    profile_type: str = typer.Option(None, "--profile-type", help="(required) Choices: ADMINISTRATOR, ADMINISTRATOR_ONLY, SUPERVISOR, PREMIUM_AGENT, STANDARD_AGENT, ANALYZER_ADMINISTRATOR, ANALYZER_SUPERVISOR, ANALYZER_USER"),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Specify whether the User profile is active or not."),
    permission_access_level: str = typer.Option(None, "--permission-access-level", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    resource_access_level: str = typer.Option(None, "--resource-access-level", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or"),
    default_resource_collection_id: str = typer.Option(None, "--default-resource-collection-id", help="Specifies the default resource collection for this profile"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new User Profile\n\nExample --json-body:\n  '{"name":"...","profileType":"ADMINISTRATOR","active":true,"permissionAccessLevel":"SPECIFIC","resourceAccessLevel":"SPECIFIC","organizationId":"...","id":"...","version":0}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if organization_id is not None:
            body["organizationId"] = organization_id
        if id_param is not None:
            body["id"] = id_param
        if version is not None:
            body["version"] = version
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if profile_type is not None:
            body["profileType"] = profile_type
        if active is not None:
            body["active"] = active
        if permission_access_level is not None:
            body["permissionAccessLevel"] = permission_access_level
        if resource_access_level is not None:
            body["resourceAccessLevel"] = resource_access_level
        if system_default is not None:
            body["systemDefault"] = system_default
        if default_resource_collection_id is not None:
            body["defaultResourceCollectionId"] = default_resource_collection_id
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        _missing = [f for f in ['name', 'profileType', 'active', 'permissionAccessLevel', 'resourceAccessLevel'] if f not in body or body[f] is None]
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



@app.command("create-bulk")
def create_bulk(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save User Profiles\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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
    id: str = typer.Argument(help="id"),
    include_names: str = typer.Option(None, "--include-names", help="Flag to include resource names in the response."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific User Profile by ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile/{id}"
    params = {}
    if include_names is not None:
        params["includeNames"] = include_names
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
    id: str = typer.Argument(help="id"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is require"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    name: str = typer.Option(None, "--name", help="The name of the user profile."),
    description: str = typer.Option(None, "--description", help="An optional description of the profile."),
    profile_type: str = typer.Option(None, "--profile-type", help="Choices: ADMINISTRATOR, ADMINISTRATOR_ONLY, SUPERVISOR, PREMIUM_AGENT, STANDARD_AGENT, ANALYZER_ADMINISTRATOR, ANALYZER_SUPERVISOR, ANALYZER_USER"),
    active: bool = typer.Option(None, "--active/--no-active", help="Specify whether the User profile is active or not."),
    permission_access_level: str = typer.Option(None, "--permission-access-level", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    resource_access_level: str = typer.Option(None, "--resource-access-level", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or"),
    default_resource_collection_id: str = typer.Option(None, "--default-resource-collection-id", help="Specifies the default resource collection for this profile"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific User Profile by ID\n\nExample --json-body:\n  '{"name":"...","profileType":"ADMINISTRATOR","active":true,"permissionAccessLevel":"SPECIFIC","resourceAccessLevel":"SPECIFIC","organizationId":"...","id":"...","version":0}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if organization_id is not None:
            body["organizationId"] = organization_id
        if id_param is not None:
            body["id"] = id_param
        if version is not None:
            body["version"] = version
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if profile_type is not None:
            body["profileType"] = profile_type
        if active is not None:
            body["active"] = active
        if permission_access_level is not None:
            body["permissionAccessLevel"] = permission_access_level
        if resource_access_level is not None:
            body["resourceAccessLevel"] = resource_access_level
        if system_default is not None:
            body["systemDefault"] = system_default
        if default_resource_collection_id is not None:
            body["defaultResourceCollectionId"] = default_resource_collection_id
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific User Profile by ID."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("list-acl")
def list_acl(
    id: str = typer.Argument(help="id"),
    names: str = typer.Option(None, "--names", help="Default all resources are returned in the ACL.     If yo"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific User Profile ACL by ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile/{id}/acl"
    params = {}
    if names is not None:
        params["names"] = names
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


