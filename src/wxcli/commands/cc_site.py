import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-site.")


@app.command("list", short_help="List Site(s).")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. Supported filterable fields: id. The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes are returned along with specified columns. All Attributes are supported"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Site(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/site"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
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



_BODY_SKELETON_CREATE = '{"name":"...","active":true,"multimediaProfileId":"...","organizationId":"...","id":"...","version":0,"description":"...","systemDefault":true,"createdTime":0,"lastUpdatedTime":0}'

@app.command("create", short_help="Create a new Site.")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. It is required to define for the following operations - All bulk save operations"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="(required) Indicates the name of the site. Generally, it is the name of the geographical location. It is required only during a create or an update operation."),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Indicates the status of the site whether it is active(when true) or not active(when false). It is required only during a create or an update operation."),
    multimedia_profile_id: str = typer.Option(None, "--multimedia-profile-id", help="(required) Indicates the multimedia profile for the site. It is required only during a create or an update operation."),
    description: str = typer.Option(None, "--description", help=""),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    created_time: str = typer.Option(None, "--created-time", help="Creation time(in epoch millis) of this resource."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="Time(in epoch millis) when this resource was last updated."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Site.\n\n\b\nExample: wxcli cc-site create --name NAME --active --multimedia-profile-id MULTIMEDIA_PROFILE_ID\n\n\b\nExample --json-body: '{"name":"...","active":true,"multimediaProfileId":"...","organizationId":"...","id":"...","version":0,"description":"...","systemDefault":true,"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/site"
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
        if active is not None:
            body["active"] = active
        if multimedia_profile_id is not None:
            body["multimediaProfileId"] = multimedia_profile_id
        if description is not None:
            body["description"] = description
        if system_default is not None:
            body["systemDefault"] = system_default
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        _missing = [f for f in ['name', 'active', 'multimediaProfileId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_BULK = '{"items":[{"itemIdentifier":0,"item":{"name":"...","active":true,"multimediaProfileId":"...","organizationId":"...","id":"...","version":0,"description":"...","systemDefault":true,"createdTime":0,"lastUpdatedTime":0},"requestAction":"..."}]}'

@app.command("create-bulk", short_help="Bulk save Site(s).")
def create_bulk(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Site(s).\n\n\b\nExample --json-body: '{"items":[{"itemIdentifier":0,"item":{"name":"...","active":true,"multimediaProfileId":"...","organizationId":"...","id":"...","version":0,"description":"...","systemDefault":true,"createdTime":0,"lastUpdatedTime":0},"requestAction":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/site/bulk"
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



@app.command("list-bulk-export", short_help="Bulk export Site(s).")
def list_bulk_export(
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk export Site(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/site/bulk-export"
    params = {}
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



@app.command("create-purge-inactive-entities", hidden=True)
@app.command("delete-purge-inactive-entities", short_help="Purge inactive Site(s).")
def delete_purge_inactive_entities(
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge batch with be selected."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Site(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/site/purge-inactive-entities"
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



@app.command("show", short_help="Get specific Site by ID.")
def show(
    id: str = typer.Argument(help="from: wxcli cc-site list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Site by ID.\n\n\b\nExample: wxcli cc-site show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/site/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","active":true,"multimediaProfileId":"...","organizationId":"...","id":"...","version":0,"description":"...","systemDefault":true,"createdTime":0,"lastUpdatedTime":0}'

@app.command("update", short_help="Update specific Site by ID.")
def update(
    id: str = typer.Argument(help="from: wxcli cc-site list"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. It is required to define for the following operations - All bulk save operations"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="Indicates the name of the site. Generally, it is the name of the geographical location. It is required only during a create or an update operation."),
    active: bool = typer.Option(None, "--active/--no-active", help="Indicates the status of the site whether it is active(when true) or not active(when false). It is required only during a create or an update operation."),
    multimedia_profile_id: str = typer.Option(None, "--multimedia-profile-id", help="Indicates the multimedia profile for the site. It is required only during a create or an update operation."),
    description: str = typer.Option(None, "--description", help=""),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    created_time: str = typer.Option(None, "--created-time", help="Creation time(in epoch millis) of this resource."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="Time(in epoch millis) when this resource was last updated."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Site by ID.\n\n\b\nExample: wxcli cc-site update ID --name NAME --active --multimedia-profile-id MULTIMEDIA_PROFILE_ID\n\n\b\nExample --json-body: '{"name":"...","active":true,"multimediaProfileId":"...","organizationId":"...","id":"...","version":0,"description":"...","systemDefault":true,"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/site/{id}"
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
        if active is not None:
            body["active"] = active
        if multimedia_profile_id is not None:
            body["multimediaProfileId"] = multimedia_profile_id
        if description is not None:
            body["description"] = description
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
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete", short_help="Delete specific Site by ID.")
def delete(
    id: str = typer.Argument(help="from: wxcli cc-site list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Site by ID.\n\n\b\nExample: wxcli cc-site delete ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"{cc_base_url}/organization/{orgid}/site/{id}"
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



@app.command("list-incoming-references", short_help="List references for a specific Site.")
def list_incoming_references(
    id: str = typer.Argument(help="UUID, from: wxcli cc-site list"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this specific entity."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific Site.\n\n\b\nExample: wxcli cc-site list-incoming-references ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/site/{id}/incoming-references"
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



@app.command("list-site", short_help="List Site(s).")
def list_site(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes are returned along with specified columns. All Attributes are supported"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Site(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/site"
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
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


