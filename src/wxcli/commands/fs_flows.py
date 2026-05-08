import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, resolve_org_id, get_cc_org_id, get_fs_base_url, get_fs_project_id


app = typer.Typer(help="Manage WxCC Flow Store fs-flows.")


@app.command("show")
def show(
    flow_id: str = typer.Argument(help="flowId"),
    view: str = typer.Option(None, "--view", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """findFlowById."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
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
    flow_id: str = typer.Argument(help="flowId"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """updateFlowById."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("update-flows")
def update_flows(
    flow_id: str = typer.Argument(help="flowId"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """mergePatchFlow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if json_body:
        body = json.loads(json_body)
    else:
        patch_op = {}
        if value is not None:
            try:
                patch_op["value"] = json.loads(value)
            except json.JSONDecodeError:
                patch_op["value"] = value
        body = [patch_op]
    try:
        result = api.session.rest_patch(url, json=body, params=params, content_type="application/json-patch+json")
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    flow_id: str = typer.Argument(help="flowId"),
    force: str = typer.Option(None, "--force", help=""),
    skip_rs_ep_check: str = typer.Option(None, "--skip-rs-ep-check", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    debug: bool = typer.Option(False, "--debug"),
):
    """removeFlowById."""
    if not force:
        typer.confirm(f"Delete {flow_id}?", abort=True)
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}"
    params = {}
    if force is not None:
        params["force"] = force
    if skip_rs_ep_check is not None:
        params["skipRsEPCheck"] = skip_rs_ep_check
    if flow_type is not None:
        params["flowType"] = flow_type
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {flow_id}")



@app.command("show-flows")
def show_flows(
    page: str = typer.Option(None, "--page", help="Defines the number of the displayed page. The page number st"),
    size: str = typer.Option(None, "--size", help="Defines the number of items to be displayed on a page. If th"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    ids: str = typer.Option(None, "--ids", help="Filters results based on a comma-separated list of flow IDs."),
    partial_name_search: str = typer.Option(None, "--partial-name-search", help="Performs a partial string match on the name of the flow. If"),
    include_pagination: str = typer.Option(None, "--include-pagination", help="If set to to true then a different paginated response object"),
    is_validation: str = typer.Option(None, "--is-validation", help="This field is used by the TM team to validate the existence"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Flows or Subflows."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows"
    params = {}
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if flow_type is not None:
        params["flowType"] = flow_type
    if ids is not None:
        params["ids"] = ids
    if partial_name_search is not None:
        params["partialNameSearch"] = partial_name_search
    if include_pagination is not None:
        params["includePagination"] = include_pagination
    if is_validation is not None:
        params["isValidation"] = is_validation
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



@app.command("create")
def create(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """saveFlow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows"
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



@app.command("create-variable-mapping")
def create_variable_mapping(
    current_flow_id: str = typer.Option(..., "--current-flow-id", help=""),
    hand_off_flow_id: str = typer.Option(..., "--hand-off-flow-id", help=""),
    hand_off_tag_id: str = typer.Option(None, "--hand-off-tag-id", help=""),
    hand_off_variable_source: str = typer.Option(None, "--hand-off-variable-source", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """performFlowVariableAutoMapping."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{orgId}/project/{project_id}/flows:variable-mapping"
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
        params["orgId"] = org_id
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



@app.command("create-unique-name")
def create_unique_name(
    flow_name: str = typer.Option(..., "--flow-name", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    flow_id: str = typer.Option(None, "--flow-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """checkFlowNameUniqueness."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:unique-name"
    params = {}
    if flow_name is not None:
        params["flowName"] = flow_name
    if flow_type is not None:
        params["flowType"] = flow_type
    if flow_id is not None:
        params["flowId"] = flow_id
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



@app.command("create-import")
def create_import(
    overwrite: str = typer.Option(None, "--overwrite", help="Determines whether to overwrite the existing flow or not. Po"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    associated_rcs: str = typer.Option(None, "--associated-rcs", help=""),
    file: str = typer.Option(None, "--file", help="(required) Multipart file to import"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Import a Flow or Subflow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:import"
    params = {}
    if overwrite is not None:
        params["overwrite"] = overwrite
    if flow_type is not None:
        params["flowType"] = flow_type
    if associated_rcs is not None:
        params["associatedRcs"] = associated_rcs
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if file is not None:
            body["file"] = file
        _missing = [f for f in ['file'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("create-copy")
def create_copy(
    source_flow_id: str = typer.Option(..., "--source-flow-id", help=""),
    associated_rcs: str = typer.Option(None, "--associated-rcs", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """copyFlow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:copy"
    params = {}
    if source_flow_id is not None:
        params["sourceFlowId"] = source_flow_id
    if associated_rcs is not None:
        params["associatedRcs"] = associated_rcs
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



@app.command("create-consume")
def create_consume(
    overwrite: str = typer.Option(None, "--overwrite", help="Determines whether to overwrite any existing flow/subflow or"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'"),
    template_name: str = typer.Option(None, "--template-name", help="Name of the Template"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new flow/subflow from the JSON string provided.."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:consume"
    params = {}
    if overwrite is not None:
        params["overwrite"] = overwrite
    if flow_type is not None:
        params["flowType"] = flow_type
    if template_name is not None:
        params["templateName"] = template_name
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



@app.command("create-consume-template")
def create_consume_template(
    overwrite: str = typer.Option(None, "--overwrite", help="Determines whether to overwrite any existing flow/subflow or"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'"),
    template_name: str = typer.Option(..., "--template-name", help="The name of the Flow/Subflow Template to be used."),
    flow_name: str = typer.Option(..., "--flow-name", help="Name of the Flow to be created/overwritten"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new flow/subflow from the template.."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
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
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """unlockFlow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:unlock"
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



@app.command("create-revert")
def create_revert(
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Option(..., "--version-id", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """revertFlowVersion."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:revert"
    params = {}
    if version_id is not None:
        params["versionId"] = version_id
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



@app.command("create-remove-rs")
def create_remove_rs(
    flow_id: str = typer.Argument(help="flowId"),
    rs_id: str = typer.Option(..., "--rs-id", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """removeRoutingStrategyFromFlow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:remove-rs"
    params = {}
    if rs_id is not None:
        params["rsId"] = rs_id
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



@app.command("create-publish")
def create_publish(
    flow_id: str = typer.Argument(help="flowId"),
    skip_validation: str = typer.Option(None, "--skip-validation", help="Skip validation of the flow before publishing."),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Publish a Flow or Subflow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:publish"
    params = {}
    if skip_validation is not None:
        params["skipValidation"] = skip_validation
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



@app.command("create-lock")
def create_lock(
    flow_id: str = typer.Argument(help="flowId"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """lockFlow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:lock"
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



@app.command("list")
def cmd_list(
    flow_id: str = typer.Argument(help="flowId"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getOrCreateDraft."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/draft"
    params = {}
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



@app.command("create-draft")
def create_draft(
    flow_id: str = typer.Argument(help="flowId"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """saveDraft."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/draft"
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



@app.command("show-search")
def show_search(
    query: str = typer.Option(..., "--query", help="Searches for flows with the given query. The search is case-"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW' or 'ALL'. Default value is 'AL"),
    page: str = typer.Option(None, "--page", help="Defines the number of the displayed page. The page number st"),
    size: str = typer.Option(None, "--size", help="Defines the number of items to be displayed on a page. If th"),
    key_value_filter: str = typer.Option(None, "--key-value-filter", help="Filters results based on key-value pairs. Format: 'key1|valu"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Flows."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows:search"
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



@app.command("show-check")
def show_check(
    view: str = typer.Option(None, "--view", help=""),
    with_draft_versions: str = typer.Option(None, "--with-draft-versions", help=""),
    skill_id: str = typer.Option(None, "--skill-id", help=""),
    ep_id: str = typer.Option(None, "--ep-id", help=""),
    flow_id: str = typer.Option(None, "--flow-id", help=""),
    global_var: str = typer.Option(None, "--global-var", help=""),
    search: str = typer.Option(None, "--search", help=""),
    business_hour: str = typer.Option(None, "--business-hour", help=""),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """findFlows_1."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
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



@app.command("show-export")
def show_export(
    flow_id: str = typer.Argument(help="flowId"),
    version: str = typer.Option(None, "--version", help="Version ID. Possible values are 'draft', 'latest' or version"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Export a Flow or Subflow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}:export"
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



@app.command("show-global-variables")
def show_global_variables(
    search: str = typer.Option(None, "--search", help=""),
    validate: str = typer.Option(None, "--validate", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getGlobalVariables."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)


