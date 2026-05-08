import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id, get_cc_org_id, get_fs_base_url, get_fs_project_id


app = typer.Typer(help="Manage WxCC Flow Store fs-flows-v2.")


@app.command("create")
def create(
    schema: str = typer.Option(None, "--schema", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Dry-run validate a FlowIr without persisting (FDL 2.0)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/flows:validate"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schema is not None:
            body["$schema"] = schema
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
    overwrite: str = typer.Option(None, "--overwrite", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    schema: str = typer.Option(None, "--schema", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Import a flow from FlowIr (FDL 2.0)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/flows:import"
    params = {}
    if overwrite is not None:
        params["overwrite"] = overwrite
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schema is not None:
            body["$schema"] = schema
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
    flow_id: str = typer.Argument(help="flowId"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get flow draft as FlowIr (FDL 2.0)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/flows/{flow_id}/draft"
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



@app.command("create-draft")
def create_draft(
    flow_id: str = typer.Argument(help="flowId"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    schema: str = typer.Option(None, "--schema", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Save flow draft from FlowIr (FDL 2.0)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/flows/{flow_id}/draft"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schema is not None:
            body["$schema"] = schema
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



@app.command("list")
def cmd_list(
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Option(None, "--version-id", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate a flow version (read-only)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/flows/{flow_id}:validate"
    params = {}
    if version_id is not None:
        params["versionId"] = version_id
    if flow_type is not None:
        params["flowType"] = flow_type
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



@app.command("show-export")
def show_export(
    flow_id: str = typer.Argument(help="flowId"),
    version: str = typer.Option(None, "--version", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Export a flow as FlowIr (FDL 2.0)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/flows/{flow_id}:export"
    params = {}
    if version is not None:
        params["version"] = version
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



@app.command("show-activities-project")
def show_activities_project(
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    check_ui_enabled: str = typer.Option(None, "--check-ui-enabled", help=""),
    search_by: str = typer.Option(None, "--search-by", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List activity definitions (FDL 2.0)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/activities"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if check_ui_enabled is not None:
        params["checkUiEnabled"] = check_ui_enabled
    if search_by is not None:
        params["searchBy"] = search_by
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



@app.command("show-activities-project-1")
def show_activities_project_1(
    activity_name: str = typer.Argument(help="activityName"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Describe a single activity (FDL 2.0)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/activities/{activity_name}"
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



@app.command("show-schema")
def show_schema(
    activity_name: str = typer.Argument(help="activityName"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get FlowIr-ready node schema for an activity (FDL 2.0)."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/activities/{activity_name}/schema"
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



@app.command("show-choices")
def show_choices(
    activity_name: str = typer.Argument(help="activityName"),
    input_name: str = typer.Argument(help="inputName"),
    search: str = typer.Option(None, "--search", help=""),
    validate: str = typer.Option(None, "--validate", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    parent_value: str = typer.Option(None, "--parent-value", help=""),
    parent_input_name: str = typer.Option(None, "--parent-input-name", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resolve dropdown/select choices for an activity input."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/v2/{org_id}/project/{project_id}/activities/{activity_name}/inputs/{input_name}/choices"
    params = {}
    if search is not None:
        params["search"] = search
    if validate is not None:
        params["validate"] = validate
    if flow_type is not None:
        params["flowType"] = flow_type
    if parent_value is not None:
        params["parentValue"] = parent_value
    if parent_input_name is not None:
        params["parentInputName"] = parent_input_name
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


