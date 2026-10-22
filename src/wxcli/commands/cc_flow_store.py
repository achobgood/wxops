import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id, resolve_org_id, get_flow_store_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center: cc-flow-store.")


@app.command("show-metadata", short_help="findFlowById.")
def show_metadata(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    view: str = typer.Option(None, "--view", help="Response view (server default: basic)"),
    flow_type: str = typer.Option(None, "--flow-type", help="FLOW or SUBFLOW (server default: FLOW)"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """findFlowById.\n\n\b\nExample: wxcli cc-flow-store show-metadata PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}"
    params = {}
    if view is not None:
        params["view"] = view
    if flow_type is not None:
        params["flowType"] = flow_type
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("update-metadata", short_help="mergePatchFlow.", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def update_metadata(ctx: typer.Context):
    """mergePatchFlow.\n\nBLOCKED: mergePatchFlow is a verified silent no-op for name/description (200, only lastModifiedDate changes). Use: wxcli cc-flow update P F --json-body '{\"name\":…}'"""
    typer.echo('mergePatchFlow is a verified silent no-op for name/description (200, only lastModifiedDate changes). Use: wxcli cc-flow update P F --json-body \'{"name":…}\'', err=True)
    raise typer.Exit(2)



@app.command("map-variables", short_help="performFlowVariableAutoMapping.")
def map_variables(
    project_id: str = typer.Argument(help="projectId"),
    current_flow_id: str = typer.Option(..., "--current-flow-id", help=""),
    hand_off_flow_id: str = typer.Option(..., "--hand-off-flow-id", help=""),
    hand_off_tag_id: str = typer.Option(None, "--hand-off-tag-id", help="Hand-off tag ID"),
    hand_off_variable_source: str = typer.Option(None, "--hand-off-variable-source", help="Hand-off variable source"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """performFlowVariableAutoMapping.\n\n\b\nExample: wxcli cc-flow-store map-variables PROJECT_ID --current-flow-id CURRENT_FLOW_ID --hand-off-flow-id HAND_OFF_FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:variable-mapping"
    params = {}
    if current_flow_id is not None:
        params["currentFlowId"] = current_flow_id
    if hand_off_flow_id is not None:
        params["handOffFlowId"] = hand_off_flow_id
    if hand_off_tag_id is not None:
        params["handOffTagId"] = hand_off_tag_id
    if hand_off_variable_source is not None:
        params["handOffVariableSource"] = hand_off_variable_source
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = get_cc_org_id(api.session)
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



@app.command("check-name", short_help="checkFlowNameUniqueness.")
def check_name(
    project_id: str = typer.Argument(help="projectId"),
    flow_name: str = typer.Option(..., "--flow-name", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help="FLOW or SUBFLOW (server default: FLOW)"),
    flow_id: str = typer.Option(None, "--flow-id", help="Exclude this flow ID (for renames)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """checkFlowNameUniqueness.\n\n\b\nExample: wxcli cc-flow-store check-name PROJECT_ID --flow-name FLOW_NAME"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:unique-name"
    params = {}
    if flow_name is not None:
        params["flowName"] = flow_name
    if flow_type is not None:
        params["flowType"] = flow_type
    if flow_id is not None:
        params["flowId"] = flow_id
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
    if isinstance(result, dict) and bool(result.get('isUnique')) != True:
        raise typer.Exit(1)



@app.command("copy", short_help="copyFlow.")
def copy(
    project_id: str = typer.Argument(help="projectId"),
    source_flow_id: str = typer.Option(..., "--source-flow-id", help=""),
    associated_rcs: str = typer.Option(None, "--associated-rcs", help="Sets the `associatedRcs` query param (associated resource collections)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """copyFlow.\n\n\b\nExample: wxcli cc-flow-store copy PROJECT_ID --source-flow-id SOURCE_FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:copy"
    params = {}
    if source_flow_id is not None:
        params["sourceFlowId"] = source_flow_id
    if associated_rcs is not None:
        params["associatedRcs"] = associated_rcs
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



@app.command("consume", short_help="Create a new flow/subflow from the JSON string provided.")
def consume(
    project_id: str = typer.Argument(help="24-char hex id"),
    overwrite: str = typer.Option(None, "--overwrite", help="Determines whether to overwrite any existing flow/subflow or not. Possible values: true/false"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'"),
    template_name: str = typer.Option(None, "--template-name", help="Name of the Template"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new flow/subflow from the JSON string provided.\n\n\b\nExample: wxcli cc-flow-store consume PROJECT_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:consume"
    params = {}
    if overwrite is not None:
        params["overwrite"] = overwrite
    if flow_type is not None:
        params["flowType"] = flow_type
    if template_name is not None:
        params["templateName"] = template_name
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    body = json.dumps(body)
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



@app.command("consume-template", short_help="Create a new flow/subflow from the template.")
def consume_template(
    project_id: str = typer.Argument(help="24-char hex id"),
    overwrite: str = typer.Option(None, "--overwrite", help="Determines whether to overwrite any existing flow/subflow or not. Possible values: true/false"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'"),
    template_name: str = typer.Option(..., "--template-name", help="The name of the Flow/Subflow Template to be used."),
    flow_name: str = typer.Option(..., "--flow-name", help="Name of the Flow to be created/overwritten"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new flow/subflow from the template.\n\n\b\nExample: wxcli cc-flow-store consume-template PROJECT_ID --template-name TEMPLATE_NAME --flow-name FLOW_NAME"""
    typer.echo("Warning: SUBFLOW templates 404 (feature-flag 'flow-control-draft-templates' gated)", err=True)
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:consume-template"
    params = {}
    if overwrite is not None:
        params["overwrite"] = overwrite
    if flow_type is not None:
        params["flowType"] = flow_type
    if template_name is not None:
        params["templateName"] = template_name
    if flow_name is not None:
        params["flowName"] = flow_name
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



@app.command("revert", short_help="revertFlowVersion.")
def revert(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Option(..., "--version-id", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help="FLOW or SUBFLOW (server default: FLOW)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """revertFlowVersion.\n\n\b\nExample: wxcli cc-flow-store revert PROJECT_ID FLOW_ID --version-id VERSION_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:revert"
    params = {}
    if version_id is not None:
        params["versionId"] = version_id
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



@app.command("test-expression", short_help="testExpression.")
def test_expression(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """testExpression.\n\nNOTE: the body is {"expr": "...", "variables": {name: value}} — variables is a MAP, e.g. --json-body '{"expr":"{{ foo }}","variables":{"foo":"bar"}}' returns generatedValue "bar". The array shape [{"name","value","type"}] returns HTTP 400 "request body is not readable" (verified live 2026-07-23, wxcc-flow test-expr)."""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    url = f"{fs_base_url}/expressionTest"
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



@app.command("show-flow-template", short_help="Get a starter flow template (FDL 2.0).")
def show_flow_template(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_name: str = typer.Option(None, "--flow-name", help="Name for the generated flow."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either 'FLOW' or 'SUBFLOW'."),
    include_ivr_menu: str = typer.Option(None, "--include-ivr-menu", help="Include an IVR menu node in the template."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a starter flow template (FDL 2.0).\n\n\b\nExample: wxcli cc-flow-store show-flow-template PROJECT_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/v2/flow-template"
    params = {}
    if flow_name is not None:
        params["flowName"] = flow_name
    if flow_type is not None:
        params["flowType"] = flow_type
    if include_ivr_menu is not None:
        params["includeIvrMenu"] = include_ivr_menu
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-usages", short_help="findFlows_1.")
def list_usages(
    project_id: str = typer.Argument(help="projectId"),
    view: str = typer.Option(None, "--view", help="Response view (server default: basic)"),
    with_draft_versions: str = typer.Option(None, "--with-draft-versions", help="yes or no (server default: no) — the server treats `true` as no"),
    skill_id: str = typer.Option(None, "--skill-id", help="Find flows using this skill ID"),
    ep_id: str = typer.Option(None, "--ep-id", help="Find flows attached to this entry point ID"),
    flow_id: str = typer.Option(None, "--flow-id", help="Restrict to one flow ID"),
    global_var: str = typer.Option(None, "--global-var", help="Find flows using this global variable"),
    search: str = typer.Option(None, "--search", help="Search term"),
    business_hour: str = typer.Option(None, "--business-hour", help="Find flows using this business-hours entity"),
    flow_type: str = typer.Option(None, "--flow-type", help="FLOW, SUBFLOW, or ALL (server default: ALL)"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """findFlows_1.\n\nNOTE: Provide at least one filter (--global-var, --ep-id, --skill-id, --business-hour, --search, --flow-id) — the server rejects unfiltered calls (400 'No search parameter provided').\n\n\b\nExample: wxcli cc-flow-store list-usages PROJECT_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:check"
    params = {}
    if view is not None:
        params["view"] = view
    if with_draft_versions is not None:
        params["withDraftVersions"] = with_draft_versions
    if skill_id is not None:
        params["skillId"] = skill_id
    if ep_id is not None:
        params["epId"] = ep_id
    if flow_id is not None:
        params["flowId"] = flow_id
    if global_var is not None:
        params["globalVar"] = global_var
    if search is not None:
        params["search"] = search
    if business_hour is not None:
        params["businessHour"] = business_hour
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Status', 'status'), ('Type', 'flowType'), ('Updated', 'lastModifiedDate')], limit=limit)



@app.command("list-global-variables", short_help="getGlobalVariables.")
def list_global_variables(
    project_id: str = typer.Argument(help="projectId"),
    search: str = typer.Option(None, "--search", help="Filter by name"),
    validate: str = typer.Option(None, "--validate", help="Sets the `validate` query param"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """getGlobalVariables.\n\n\b\nExample: wxcli cc-flow-store list-global-variables PROJECT_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/global-variables"
    params = {}
    if search is not None:
        params["search"] = search
    if validate is not None:
        params["validate"] = validate
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-health", short_help="health.")
def show_health(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """health."""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    url = f"{fs_base_url}/health"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-build-info", short_help="buildInfo.")
def show_build_info(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """buildInfo."""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    url = f"{fs_base_url}/build_info"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-current-user", short_help="getCurrentUser.")
def show_current_user(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """getCurrentUser."""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    url = f"{fs_base_url}/auth/user"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


