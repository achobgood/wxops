import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-flow.")


@app.command("list")
def cmd_list(
    project_id: str = typer.Argument(help="projectId"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    ids: str = typer.Option(None, "--ids", help="Filters results based on a comma-separated list of flow IDs."),
    page: str = typer.Option(None, "--page", help="Defines the number of the displayed page. The page number st"),
    partial_name_search: str = typer.Option(None, "--partial-name-search", help="Performs a partial string match on the name of the flow. If"),
    search_by: str = typer.Option(None, "--search-by", help="Filter expression in the format `<field>|<value>`. Supports"),
    size: str = typer.Option(None, "--size", help="Defines the number of items to be displayed on a page. If th"),
    include_pagination: str = typer.Option(None, "--include-pagination", help="If set to true then a different paginated response object co"),
    is_validation: str = typer.Option(None, "--is-validation", help="If true, validates the existence of flows by ID regardless o"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Flows or Subflows."""
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
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("publish")
def publish(
    flow_id: str = typer.Argument(help="flowId"),
    project_id: str = typer.Argument(help="projectId"),
    skip_validation: str = typer.Option(None, "--skip-validation", help="If true, the flow's pre-publish validation is skipped. Use w"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    comment: str = typer.Option(None, "--comment", help="A comment to provide context on publishing the flow."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Publish a Flow or Subflow\n\nExample --json-body:\n  '{"comment":"...","tagIds":["..."]}'."""
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
        body = json.loads(json_body)
    else:
        body = {}
        if comment is not None:
            body["comment"] = comment
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



@app.command("create-lock")
def create_lock(
    flow_id: str = typer.Argument(help="flowId"),
    project_id: str = typer.Argument(help="projectId"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Lock a Flow or Subflow."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:lock"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



@app.command("create-unlock")
def create_unlock(
    flow_id: str = typer.Argument(help="flowId"),
    project_id: str = typer.Argument(help="projectId"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unlock a Flow or Subflow."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:unlock"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



@app.command("create-validate")
def create_validate(
    project_id: str = typer.Argument(help="projectId"),
    flow_name: str = typer.Option(None, "--flow-name", help="Name of the flow."),
    flow_type: str = typer.Option(None, "--flow-type", help="Choices: FLOW, SUBFLOW"),
    contact_type: str = typer.Option(None, "--contact-type", help="Channel type the flow is intended for (for example, `telepho"),
    description: str = typer.Option(None, "--description", help="Human-readable description of the flow."),
    version: str = typer.Option(None, "--version", help="Monotonically increasing version number of the document."),
    status: str = typer.Option(None, "--status", help="Choices: Draft, Published"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate a Flow\n\nExample --json-body:\n  '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":"...","outputs":"...","position":"..."}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows:validate"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-import")
def create_import(
    project_id: str = typer.Argument(help="projectId"),
    overwrite: str = typer.Option(None, "--overwrite", help="If true, replaces an existing flow with the same name. Defau"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    flow_name: str = typer.Option(None, "--flow-name", help="Name of the flow."),
    contact_type: str = typer.Option(None, "--contact-type", help="Channel type the flow is intended for (for example, `telepho"),
    description: str = typer.Option(None, "--description", help="Human-readable description of the flow."),
    version: str = typer.Option(None, "--version", help="Monotonically increasing version number of the document."),
    status: str = typer.Option(None, "--status", help="Choices: Draft, Published"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Import a Flow\n\nExample --json-body:\n  '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":"...","outputs":"...","position":"..."}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}'."""
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
        body = json.loads(json_body)
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
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="flowId"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Flow."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("create-flows")
def create_flows(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="flowId"),
    expected_version: str = typer.Option(None, "--expected-version", help="Expected current draft version for optimistic locking. The r"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    flow_name: str = typer.Option(None, "--flow-name", help="Name of the flow."),
    contact_type: str = typer.Option(None, "--contact-type", help="Channel type the flow is intended for (for example, `telepho"),
    description: str = typer.Option(None, "--description", help="Human-readable description of the flow."),
    version: str = typer.Option(None, "--version", help="Monotonically increasing version number of the document."),
    status: str = typer.Option(None, "--status", help="Choices: Draft, Published"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Save a Flow Draft\n\nExample --json-body:\n  '{"flowName":"...","flowType":"FLOW","contactType":"...","description":"...","version":0,"status":"Draft","nodes":[{"name":"...","activityName":"...","inputs":"...","outputs":"...","position":"..."}],"edges":[{"key":"...","from_node":"...","from_port":"...","to_node":"...","condition":"..."}]}'."""
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
        body = json.loads(json_body)
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
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="flowId"),
    expected_version: str = typer.Option(None, "--expected-version", help="Expected current draft version for optimistic locking. The r"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Patch a Flow Draft\n\nExample --json-body:\n  '{"upsert_nodes":[{}],"upsert_edges":[{}],"remove_node_names":["..."],"remove_edge_keys":["..."]}'."""
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
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-validate")
def list_validate(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Option(None, "--version-id", help="Version to validate. Use 'draft' for the current draft, or a"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate an Existing Flow Draft."""
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
    result = result or []
    items = result.get("results", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("export")
def export(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="flowId"),
    version: str = typer.Option(None, "--version", help="Version to export. Use 'latest' for the most recent publishe"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Export a Flow."""
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
    result = result or []
    items = result.get("nodes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


