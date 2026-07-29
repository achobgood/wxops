import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-flow.")


@app.command("list", short_help="List Flows or Subflows.")
def cmd_list(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    ids: str = typer.Option(None, "--ids", help="Filters results based on a comma-separated list of flow IDs. If provided, only flows with those IDs will be fetched in the response."),
    page: str = typer.Option(None, "--page", help="Defines the number of the displayed page. The page number starts from 0."),
    partial_name_search: str = typer.Option(None, "--partial-name-search", help="Performs a partial string match on the name of the flow. If the flow name contains the given string it will be fetched in the response."),
    search_by: str = typer.Option(None, "--search-by", help="Filter expression in the format `<field>|<value>`. Supports searching by `channelType` (for example, `channelType|telephony`, `channelType|workItem`, `channelType|customMessaging`, `channelType|genericAction`)."),
    size: str = typer.Option(None, "--size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    include_pagination: str = typer.Option(None, "--include-pagination", help="If set to true then a different paginated response object containing the page metadata (currentPage, totalRecords, pageSize, totalPages) will be returned. The flow objects will be in an array named \"data\"."),
    is_validation: str = typer.Option(None, "--is-validation", help="If true, validates the existence of flows by ID regardless of the caller's RBAC access. Intended for internal Task Management use cases."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Flows or Subflows.\n\n\b\nExample: wxcli cc-flow list PROJECT_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/flows"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if ids is not None:
        params["ids"] = ids
    if page is not None:
        params["page"] = page
    if partial_name_search is not None:
        params["partialNameSearch"] = partial_name_search
    if search_by is not None:
        params["searchBy"] = search_by
    if size is not None:
        params["size"] = size
    if include_pagination is not None:
        params["includePagination"] = include_pagination
    if is_validation is not None:
        params["isValidation"] = is_validation
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Created By', 'createdBy'), ('Created Date', 'createdDate'), ('Description', 'description')], limit=limit)



@app.command("list-search", short_help="Search Flows.")
def list_search(
    project_id: str = typer.Argument(help="24-char hex id"),
    query: str = typer.Option(..., "--query", help="Searches for flows with the given query. The search is case-sensitive."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW' or 'ALL'. Default value is 'ALL'."),
    page: str = typer.Option(None, "--page", help="Defines the number of the displayed page. The page number starts from 0."),
    size: str = typer.Option(None, "--size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    key_value_filter: str = typer.Option(None, "--key-value-filter", help="Filters results based on key-value pairs. Format: 'key1|value1,key2|value2'. This will add a filter on normalizedFlow collection directly instead of running query on atlas."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Flows.\n\n\b\nExample: wxcli cc-flow list-search PROJECT_ID --query QUERY"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/flows:search"
    params = {}
    if query is not None:
        params["query"] = query
    if flow_type is not None:
        params["flowType"] = flow_type
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if key_value_filter is not None:
        params["keyValueFilter"] = key_value_filter
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Flow Type', 'flowType'), ('Last Modified Date', 'lastModifiedDate')], limit=limit)



@app.command("delete", short_help="Delete a Flow or Subflow.")
def delete(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="24-char hex id, from: wxcli cc-flow list"),
    force: str = typer.Option(None, "--force", help="If 'yes', the flow is deleted even if it is still referenced by other entities. Defaults to 'no'."),
    skip_rs_ep_check: str = typer.Option(None, "--skip-rs-ep-check", help="If true, skips the check for routing strategy and entry point associations before deleting the flow."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Flow or Subflow.\n\n\b\nExample: wxcli cc-flow delete PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {flow_id}?", abort=True)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/flows/{flow_id}"
    params = {}
    if force is not None:
        params["force"] = force
    if skip_rs_ep_check is not None:
        params["skipRsEPCheck"] = skip_rs_ep_check
    if flow_type is not None:
        params["flowType"] = flow_type
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {flow_id}")
    else:
        emit({"status": "deleted", "id": flow_id}, output=output, fields=fields)



_BODY_SKELETON_PUBLISH = '{"comment":"...","tagIds":["..."]}'

@app.command("create", hidden=True)
@app.command("publish", short_help="Publish a Flow or Subflow.")
def publish(
    flow_id: str = typer.Argument(help="24-char hex id"),
    project_id: str = typer.Argument(help="24-char hex id"),
    skip_validation: str = typer.Option(None, "--skip-validation", help="If true, the flow's pre-publish validation is skipped. Use with care."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    comment: str = typer.Option(None, "--comment", help="A comment to provide context on publishing the flow."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Publish a Flow or Subflow.\n\n\b\nExample: wxcli cc-flow publish FLOW_ID PROJECT_ID\n\n\b\nExample --json-body: '{"comment":"...","tagIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_PUBLISH), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:publish"
    params = {}
    if skip_validation is not None:
        params["skipValidation"] = skip_validation
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if comment is not None:
            body["comment"] = comment
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



@app.command("create-lock", short_help="Lock a Flow or Subflow.")
def create_lock(
    flow_id: str = typer.Argument(help="24-char hex id"),
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Lock a Flow or Subflow.\n\n\b\nExample: wxcli cc-flow create-lock FLOW_ID PROJECT_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:lock"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
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
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("create-unlock", short_help="Unlock a Flow or Subflow.")
def create_unlock(
    flow_id: str = typer.Argument(help="24-char hex id"),
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unlock a Flow or Subflow.\n\n\b\nExample: wxcli cc-flow create-unlock FLOW_ID PROJECT_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:unlock"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
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
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_VALIDATE = '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}],"variables":[{"name":"...","type":"...","value":"...","description":"...","isCAD":true,"isAgentEditable":true,"isReportable":true,"isSecure":true}],"eventFlows":[{"event":"...","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}],"preferences":[{"name":"...","type":"...","value":"..."}]}'

@app.command("create-validate", short_help="Validate a Flow.")
def create_validate(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_name: str = typer.Option(None, "--flow-name", help="Name of the flow."),
    flow_type: str = typer.Option(None, "--flow-type", help="Choices: FLOW, SUBFLOW"),
    contact_type: str = typer.Option(None, "--contact-type", help="Channel type the flow is intended for (for example, `telephony`, `customMessaging`, `workItem`, `genericAction`)."),
    description: str = typer.Option(None, "--description", help="Human-readable description of the flow."),
    version: str = typer.Option(None, "--version", help="Monotonically increasing version number of the document."),
    status: str = typer.Option(None, "--status", help="Choices: Draft, Published"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate a Flow.\n\n\b\nExample: wxcli cc-flow create-validate PROJECT_ID\n\n\b\nExample --json-body: '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}],"variables":[{"name":"...","type":"...","value":"...","description":"...","isCAD":true,"isAgentEditable":true,"isReportable":true,"isSecure":true}],"eventFlows":[{"event":"...","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}],"preferences":[{"name":"...","type":"...","value":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_VALIDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows:validate"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if flow_name is not None:
            body["flowName"] = flow_name
        if flow_type is not None:
            body["flowType"] = flow_type
        if contact_type is not None:
            body["contactType"] = contact_type
        if description is not None:
            body["description"] = description
        if version is not None:
            body["version"] = version
        if status is not None:
            body["status"] = status
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



_BODY_SKELETON_CREATE_IMPORT = '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}],"variables":[{"name":"...","type":"...","value":"...","description":"...","isCAD":true,"isAgentEditable":true,"isReportable":true,"isSecure":true}],"eventFlows":[{"event":"...","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}],"preferences":[{"name":"...","type":"...","value":"..."}]}'

@app.command("create-import", short_help="Import a Flow.")
def create_import(
    project_id: str = typer.Argument(help="24-char hex id"),
    overwrite: str = typer.Option(None, "--overwrite", help="If true, replaces an existing flow with the same name. Defaults to false."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    flow_name: str = typer.Option(None, "--flow-name", help="Name of the flow."),
    contact_type: str = typer.Option(None, "--contact-type", help="Channel type the flow is intended for (for example, `telephony`, `customMessaging`, `workItem`, `genericAction`)."),
    description: str = typer.Option(None, "--description", help="Human-readable description of the flow."),
    version: str = typer.Option(None, "--version", help="Monotonically increasing version number of the document."),
    status: str = typer.Option(None, "--status", help="Choices: Draft, Published"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Import a Flow.\n\n\b\nExample: wxcli cc-flow create-import PROJECT_ID\n\n\b\nExample --json-body: '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}],"variables":[{"name":"...","type":"...","value":"...","description":"...","isCAD":true,"isAgentEditable":true,"isReportable":true,"isSecure":true}],"eventFlows":[{"event":"...","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}],"preferences":[{"name":"...","type":"...","value":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_IMPORT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows:import"
    params = {}
    if overwrite is not None:
        params["overwrite"] = overwrite
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if flow_name is not None:
            body["flowName"] = flow_name
        if contact_type is not None:
            body["contactType"] = contact_type
        if description is not None:
            body["description"] = description
        if version is not None:
            body["version"] = version
        if status is not None:
            body["status"] = status
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



@app.command("show", short_help="Get a Flow.")
def show(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="24-char hex id, from: wxcli cc-flow list"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Flow.\n\n\b\nExample: wxcli cc-flow show PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows/{flow_id}"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_FLOWS = '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}],"variables":[{"name":"...","type":"...","value":"...","description":"...","isCAD":true,"isAgentEditable":true,"isReportable":true,"isSecure":true}],"eventFlows":[{"event":"...","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}],"preferences":[{"name":"...","type":"...","value":"..."}]}'

@app.command("create-flows", short_help="Save a Flow Draft.")
def create_flows(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="24-char hex id, from: wxcli cc-flow list"),
    expected_version: str = typer.Option(None, "--expected-version", help="Expected current draft version for optimistic locking. The request fails with 409 Conflict if the server-side version does not match. Omit to skip the check."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    flow_name: str = typer.Option(None, "--flow-name", help="Name of the flow."),
    contact_type: str = typer.Option(None, "--contact-type", help="Channel type the flow is intended for (for example, `telephony`, `customMessaging`, `workItem`, `genericAction`)."),
    description: str = typer.Option(None, "--description", help="Human-readable description of the flow."),
    version: str = typer.Option(None, "--version", help="Monotonically increasing version number of the document."),
    status: str = typer.Option(None, "--status", help="Choices: Draft, Published"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Save a Flow Draft.\n\n\b\nExample: wxcli cc-flow create-flows PROJECT_ID FLOW_ID\n\n\b\nExample --json-body: '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}],"variables":[{"name":"...","type":"...","value":"...","description":"...","isCAD":true,"isAgentEditable":true,"isReportable":true,"isSecure":true}],"eventFlows":[{"event":"...","nodes":[{"name":"...","activityName":"...","inputs":{},"outputs":{},"position":{"x":0,"y":0}}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}],"preferences":[{"name":"...","type":"...","value":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_FLOWS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows/{flow_id}"
    params = {}
    if expected_version is not None:
        params["expectedVersion"] = expected_version
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if flow_name is not None:
            body["flowName"] = flow_name
        if contact_type is not None:
            body["contactType"] = contact_type
        if description is not None:
            body["description"] = description
        if version is not None:
            body["version"] = version
        if status is not None:
            body["status"] = status
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



_BODY_SKELETON_UPDATE = '{"upsert_nodes":[{}],"upsert_edges":[{}],"remove_node_names":["..."],"remove_edge_keys":["..."]}'

@app.command("update", short_help="Patch a Flow Draft.")
def update(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="24-char hex id, from: wxcli cc-flow list"),
    expected_version: str = typer.Option(None, "--expected-version", help="Expected current draft version for optimistic locking. The request fails with 409 Conflict if the server-side version does not match. Omit to skip the check."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Patch a Flow Draft.\n\n\b\nExample: wxcli cc-flow update PROJECT_ID FLOW_ID\n\n\b\nExample --json-body: '{"upsert_nodes":[{}],"upsert_edges":[{}],"remove_node_names":["..."],"remove_edge_keys":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows/{flow_id}"
    params = {}
    if expected_version is not None:
        params["expectedVersion"] = expected_version
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": flow_id}, output=output, fields=fields)



@app.command("list-validate", short_help="Validate an Existing Flow Draft.")
def list_validate(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="24-char hex id"),
    version_id: str = typer.Option(None, "--version-id", help="Version to validate. Use 'draft' for the current draft, or a specific version ObjectId."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate an Existing Flow Draft.\n\n\b\nExample: wxcli cc-flow list-validate PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows/{flow_id}:validate"
    params = {}
    if version_id is not None:
        params["versionId"] = version_id
    if flow_type is not None:
        params["flowType"] = flow_type
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
    items = result.get("results", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Code', 'code'), ('Doc Link', 'docLink'), ('Hint', 'hint'), ('Message', 'message'), ('Severity', 'severity')], limit=limit)



@app.command("list-export", hidden=True)
@app.command("export", short_help="Export a Flow.")
def export(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="24-char hex id"),
    version: str = typer.Option(None, "--version", help="Version to export. Use 'latest' for the most recent published version, 'draft' for the working copy, or a specific version ObjectId."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Export a Flow.\n\n\b\nExample: wxcli cc-flow export PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows/{flow_id}:export"
    params = {}
    if version is not None:
        params["version"] = version
    if flow_type is not None:
        params["flowType"] = flow_type
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
    items = result.get("nodes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Name', 'name'), ('Activity Name', 'activityName')], limit=limit)


