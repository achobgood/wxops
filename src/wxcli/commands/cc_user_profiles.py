import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center cc-user-profiles.")


@app.command("list", short_help="List references for a specific User Profile.")
def cmd_list(
    id: str = typer.Argument(help="UUID"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this specific entity."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific User Profile.\n\n\b\nExample: wxcli cc-user-profiles list ID"""
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
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-user-profile", short_help="List user profiles.")
def list_user_profile(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, userProfileAppModules, entryPoints, sites, queues, teams, editableFolderIds, viewableFolderIds, nonViewableFolderIds, createdTime, lastUpdatedTime The examples below show some search..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported. except (entryPoints,sites, queues, teams, userProfileAppModules,editableFolderIds, viewableFolderIds, nonViewableFolderIds)"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name, profileType, description) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\",\"description\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","profileType":"ADMINISTRATOR","active":true,"permissionAccessLevel":"SPECIFIC","resourceAccessLevel":"SPECIFIC","organizationId":"...","id":"...","version":0,"description":"...","permissions":[{"name":"...","id":"...","access":"EDIT"}],"editableFolderIds":[0],"viewableFolderIds":[0],"nonViewableFolderIds":[0],"systemDefault":true,"defaultResourceCollectionId":"...","resourceCollections":[{"name":"...","organizationId":"...","id":"...","version":0,"description":"...","resources":[{"name":"...","accessLevel":"SPECIFIC","ids":["..."]}],"resourceCount":0,"createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0}'

@app.command("create", short_help="Create a new User Profile.")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="(required) The name of the user profile."),
    description: str = typer.Option(None, "--description", help="An optional description of the profile."),
    profile_type: str = typer.Option(None, "--profile-type", help="(required) Choices: ADMINISTRATOR, ADMINISTRATOR_ONLY, SUPERVISOR, PREMIUM_AGENT, STANDARD_AGENT, ANALYZER_ADMINISTRATOR, ANALYZER_SUPERVISOR, ANALYZER_USER"),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Specify whether the User profile is active or not."),
    permission_access_level: str = typer.Option(None, "--permission-access-level", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    resource_access_level: str = typer.Option(None, "--resource-access-level", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    default_resource_collection_id: str = typer.Option(None, "--default-resource-collection-id", help="Specifies the default resource collection for this profile"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new User Profile.\n\n\b\nExample: wxcli cc-user-profiles create --name NAME --profile-type ADMINISTRATOR --active --permission-access-level SPECIFIC --resource-access-level SPECIFIC\n\n\b\nExample --json-body: '{"name":"...","profileType":"ADMINISTRATOR","active":true,"permissionAccessLevel":"SPECIFIC","resourceAccessLevel":"SPECIFIC","organizationId":"...","id":"...","version":0,"description":"...","permissions":[{"name":"...","id":"...","access":"EDIT"}],"editableFolderIds":[0],"viewableFolderIds":[0],"nonViewableFolderIds":[0],"systemDefault":true,"defaultResourceCollectionId":"...","resourceCollections":[{"name":"...","organizationId":"...","id":"...","version":0,"description":"...","resources":[{"name":"...","accessLevel":"SPECIFIC","ids":["..."]}],"resourceCount":0,"createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile"
    if json_body:
        body = load_json_body(json_body)
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



_BODY_SKELETON_CREATE_BULK = '{"items":[{"itemIdentifier":0,"item":{"name":"...","profileType":"ADMINISTRATOR","active":true,"permissionAccessLevel":"SPECIFIC","resourceAccessLevel":"SPECIFIC","organizationId":"...","id":"...","version":0,"description":"...","permissions":[{"name":"...","id":"...","access":"EDIT"}],"editableFolderIds":[0],"viewableFolderIds":[0],"nonViewableFolderIds":[0],"systemDefault":true,"defaultResourceCollectionId":"...","resourceCollections":[{"name":"...","organizationId":"...","id":"...","version":0,"description":"...","resources":[{"name":"...","accessLevel":"SPECIFIC","ids":["..."]}],"resourceCount":0,"createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0},"requestAction":"..."}]}'

@app.command("create-bulk", short_help="Bulk save User Profiles.")
def create_bulk(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save User Profiles.\n\n\b\nExample --json-body: '{"items":[{"itemIdentifier":0,"item":{"name":"...","profileType":"ADMINISTRATOR","active":true,"permissionAccessLevel":"SPECIFIC","resourceAccessLevel":"SPECIFIC","organizationId":"...","id":"...","version":0,"description":"...","permissions":[{"name":"...","id":"...","access":"EDIT"}],"editableFolderIds":[0],"viewableFolderIds":[0],"nonViewableFolderIds":[0],"systemDefault":true,"defaultResourceCollectionId":"...","resourceCollections":[{"name":"...","organizationId":"...","id":"...","version":0,"description":"...","resources":[{"name":"...","accessLevel":"SPECIFIC","ids":["..."]}],"resourceCount":0,"createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0},"requestAction":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile/bulk"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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



@app.command("show", short_help="Get specific User Profile by ID.")
def show(
    id: str = typer.Argument(help="UUID, from: wxcli cc-user-profiles list-user-profile"),
    include_names: str = typer.Option(None, "--include-names", help="Flag to include resource names in the response."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific User Profile by ID.\n\n\b\nExample: wxcli cc-user-profiles show ID"""
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","profileType":"ADMINISTRATOR","active":true,"permissionAccessLevel":"SPECIFIC","resourceAccessLevel":"SPECIFIC","organizationId":"...","id":"...","version":0,"description":"...","permissions":[{"name":"...","id":"...","access":"EDIT"}],"editableFolderIds":[0],"viewableFolderIds":[0],"nonViewableFolderIds":[0],"systemDefault":true,"defaultResourceCollectionId":"...","resourceCollections":[{"name":"...","organizationId":"...","id":"...","version":0,"description":"...","resources":[{"name":"...","accessLevel":"SPECIFIC","ids":["..."]}],"resourceCount":0,"createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0}'

@app.command("update", short_help="Update specific User Profile by ID.")
def update(
    id: str = typer.Argument(help="UUID, from: wxcli cc-user-profiles list-user-profile"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="The name of the user profile."),
    description: str = typer.Option(None, "--description", help="An optional description of the profile."),
    profile_type: str = typer.Option(None, "--profile-type", help="Choices: ADMINISTRATOR, ADMINISTRATOR_ONLY, SUPERVISOR, PREMIUM_AGENT, STANDARD_AGENT, ANALYZER_ADMINISTRATOR, ANALYZER_SUPERVISOR, ANALYZER_USER"),
    active: bool = typer.Option(None, "--active/--no-active", help="Specify whether the User profile is active or not."),
    permission_access_level: str = typer.Option(None, "--permission-access-level", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    resource_access_level: str = typer.Option(None, "--resource-access-level", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    default_resource_collection_id: str = typer.Option(None, "--default-resource-collection-id", help="Specifies the default resource collection for this profile"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific User Profile by ID.\n\n\b\nExample: wxcli cc-user-profiles update ID --name NAME --profile-type ADMINISTRATOR --active --permission-access-level SPECIFIC --resource-access-level SPECIFIC\n\n\b\nExample --json-body: '{"name":"...","profileType":"ADMINISTRATOR","active":true,"permissionAccessLevel":"SPECIFIC","resourceAccessLevel":"SPECIFIC","organizationId":"...","id":"...","version":0,"description":"...","permissions":[{"name":"...","id":"...","access":"EDIT"}],"editableFolderIds":[0],"viewableFolderIds":[0],"nonViewableFolderIds":[0],"systemDefault":true,"defaultResourceCollectionId":"...","resourceCollections":[{"name":"...","organizationId":"...","id":"...","version":0,"description":"...","resources":[{"name":"...","accessLevel":"SPECIFIC","ids":["..."]}],"resourceCount":0,"createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete", short_help="Delete specific User Profile by ID.")
def delete(
    id: str = typer.Argument(help="UUID, from: wxcli cc-user-profiles list-user-profile"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific User Profile by ID.\n\n\b\nExample: wxcli cc-user-profiles delete ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"{cc_base_url}/organization/{orgid}/v3/user-profile/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-acl", short_help="Get specific User Profile ACL by ID.")
def list_acl(
    id: str = typer.Argument(help="UUID, from: wxcli cc-user-profiles list-user-profile"),
    names: str = typer.Option(None, "--names", help="Default all resources are returned in the ACL. If you want to filter the ACL by specific resources, provide a comma-separated list of resource names to filter the ACL. Ex: /url?names=site,team"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific User Profile ACL by ID.\n\n\b\nExample: wxcli cc-user-profiles list-acl ID"""
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


