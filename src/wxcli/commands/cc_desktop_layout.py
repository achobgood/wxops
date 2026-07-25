import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-desktop-layout.")


_BODY_SKELETON_CREATE = '{"name":"...","editedBy":"...","jsonFileName":"...","jsonFileContent":"...","global":true,"status":true,"defaultJsonModified":true,"validated":true}'

@app.command("create")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="(required) A name for the Desktop Layout."),
    description: str = typer.Option(None, "--description", help="A short description indicating the context of the Desktop Layout."),
    edited_by: str = typer.Option(None, "--edited-by", help="(required) Indicates who modified the Desktop Layout."),
    json_file_name: str = typer.Option(None, "--json-file-name", help="(required) Enter the name of the file."),
    json_file_content: str = typer.Option(None, "--json-file-content", help="(required) Enter the Desktop Layout json."),
    global_param: bool = typer.Option(None, "--global/--no-global", help="(required) Indicates if the Desktop Layout is a global layout or a custom layout."),
    status: bool = typer.Option(None, "--status/--no-status", help="(required) Indicates if the Desktop Layout is in active state or inactive."),
    default_json_modified: bool = typer.Option(None, "--default-json-modified/--no-default-json-modified", help="(required) Indicates if the default Desktop Layout is modified."),
    validated: bool = typer.Option(None, "--validated/--no-validated", help="(required) Indicates if the Desktop Layout is validated."),
    validated_time: str = typer.Option(None, "--validated-time", help="Validated time(in epoch milliseconds) of this resource."),
    default_json_modified_time: str = typer.Option(None, "--default-json-modified-time", help="Default Json Modified time(in epoch milliseconds) of this resource."),
    modified_time: str = typer.Option(None, "--modified-time", help="Modified time(in epoch milliseconds) of this resource."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Desktop Layout\n\nExample --json-body:\n  '{"name":"...","editedBy":"...","jsonFileName":"...","jsonFileContent":"...","global":true,"status":true,"defaultJsonModified":true,"validated":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/desktop-layout"
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
        if edited_by is not None:
            body["editedBy"] = edited_by
        if json_file_name is not None:
            body["jsonFileName"] = json_file_name
        if json_file_content is not None:
            body["jsonFileContent"] = json_file_content
        if global_param is not None:
            body["global"] = global_param
        if status is not None:
            body["status"] = status
        if default_json_modified is not None:
            body["defaultJsonModified"] = default_json_modified
        if validated is not None:
            body["validated"] = validated
        if validated_time is not None:
            body["validatedTime"] = validated_time
        if default_json_modified_time is not None:
            body["defaultJsonModifiedTime"] = default_json_modified_time
        if modified_time is not None:
            body["modifiedTime"] = modified_time
        if system_default is not None:
            body["systemDefault"] = system_default
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        _missing = [f for f in ['name', 'editedBy', 'jsonFileName', 'jsonFileContent', 'global', 'status', 'defaultJsonModified', 'validated'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_BULK = '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'

@app.command("create-bulk")
def create_bulk(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Desktop Layout(s)\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/desktop-layout/bulk"
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



@app.command("create-purge-inactive-entities")
def create_purge_inactive_entities(
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge batch with be selected."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Desktop Layout(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/desktop-layout/purge-inactive-entities"
    params = {}
    if next_start_id is not None:
        params["nextStartId"] = next_start_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        typer.echo("Purged.")
    else:
        emit(result, output=output, fields=fields)



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Desktop Layout by ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/desktop-layout/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","editedBy":"...","jsonFileName":"...","jsonFileContent":"...","global":true,"status":true,"defaultJsonModified":true,"validated":true}'

@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="A name for the Desktop Layout."),
    description: str = typer.Option(None, "--description", help="A short description indicating the context of the Desktop Layout."),
    edited_by: str = typer.Option(None, "--edited-by", help="Indicates who modified the Desktop Layout."),
    json_file_name: str = typer.Option(None, "--json-file-name", help="Enter the name of the file."),
    json_file_content: str = typer.Option(None, "--json-file-content", help="Enter the Desktop Layout json."),
    global_param: bool = typer.Option(None, "--global/--no-global", help="Indicates if the Desktop Layout is a global layout or a custom layout."),
    status: bool = typer.Option(None, "--status/--no-status", help="Indicates if the Desktop Layout is in active state or inactive."),
    default_json_modified: bool = typer.Option(None, "--default-json-modified/--no-default-json-modified", help="Indicates if the default Desktop Layout is modified."),
    validated: bool = typer.Option(None, "--validated/--no-validated", help="Indicates if the Desktop Layout is validated."),
    validated_time: str = typer.Option(None, "--validated-time", help="Validated time(in epoch milliseconds) of this resource."),
    default_json_modified_time: str = typer.Option(None, "--default-json-modified-time", help="Default Json Modified time(in epoch milliseconds) of this resource."),
    modified_time: str = typer.Option(None, "--modified-time", help="Modified time(in epoch milliseconds) of this resource."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Desktop Layout by ID\n\nExample --json-body:\n  '{"name":"...","editedBy":"...","jsonFileName":"...","jsonFileContent":"...","global":true,"status":true,"defaultJsonModified":true,"validated":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/desktop-layout/{id}"
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
        if edited_by is not None:
            body["editedBy"] = edited_by
        if json_file_name is not None:
            body["jsonFileName"] = json_file_name
        if json_file_content is not None:
            body["jsonFileContent"] = json_file_content
        if global_param is not None:
            body["global"] = global_param
        if status is not None:
            body["status"] = status
        if default_json_modified is not None:
            body["defaultJsonModified"] = default_json_modified
        if validated is not None:
            body["validated"] = validated
        if validated_time is not None:
            body["validatedTime"] = validated_time
        if default_json_modified_time is not None:
            body["defaultJsonModifiedTime"] = default_json_modified_time
        if modified_time is not None:
            body["modifiedTime"] = modified_time
        if system_default is not None:
            body["systemDefault"] = system_default
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
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Desktop Layout by ID."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/desktop-layout/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Deleted: {id}")



@app.command("list")
def cmd_list(
    id: str = typer.Argument(help="id"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this specific entity."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific Desktop Layout."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/desktop-layout/{id}/incoming-references"
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
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-desktop-layout")
def list_desktop_layout(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, validatedTime, defaultJsonModifiedTime, modifiedTime, teamIds, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported."),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, This query param should use only if the response contain single record, if we are using for multiple objects response query param not supported and throws an exception."),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that user has access to, according to User Profile."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Desktop Layout(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/desktop-layout"
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
    if single_object_response is not None:
        params["singleObjectResponse"] = single_object_response
    if provisioning_view is not None:
        params["provisioningView"] = provisioning_view
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


