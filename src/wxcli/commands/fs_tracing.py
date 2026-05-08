import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id, get_cc_org_id, get_fs_base_url, get_fs_project_id


app = typer.Typer(help="Manage WxCC Flow Store fs-tracing.")


@app.command("show")
def show(
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Argument(help="versionId"),
    interaction_id: str = typer.Argument(help="interactionId"),
    convert_ids: str = typer.Option(None, "--convert-ids", help="Converts process IDs to diagram IDs. Possible values: 'true'"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get interaction metadata of a Flow Version object."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/{version_id}/interaction/{interaction_id}"
    params = {}
    if convert_ids is not None:
        params["convertIds"] = convert_ids
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



@app.command("list")
def cmd_list(
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Argument(help="versionId"),
    interaction_id: str = typer.Argument(help="interactionId"),
    current_page: str = typer.Option(None, "--current-page", help="index of the current page for pagination"),
    page_size: str = typer.Option(None, "--page-size", help="determines the number of records in a page"),
    process_id: str = typer.Option(None, "--process-id", help="processId of the flow version"),
    doc_id: str = typer.Option(None, "--doc-id", help="document id of the flow trace"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get traces by interaction ID of a Flow Version object."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/{version_id}/interaction/{interaction_id}/traces"
    params = {}
    if current_page is not None:
        params["currentPage"] = current_page
    if page_size is not None:
        params["pageSize"] = page_size
    if process_id is not None:
        params["processId"] = process_id
    if doc_id is not None:
        params["docId"] = doc_id
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



@app.command("list-decrypt")
def list_decrypt(
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Argument(help="versionId"),
    interaction_id: str = typer.Argument(help="interactionId"),
    process_id: str = typer.Option(..., "--process-id", help="processId of the flow version"),
    doc_id: str = typer.Option(None, "--doc-id", help="document id of the flow trace"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get traces by interaction ID of a Flow Version object."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/{version_id}/interaction/{interaction_id}/traces:decrypt"
    params = {}
    if process_id is not None:
        params["processId"] = process_id
    if doc_id is not None:
        params["docId"] = doc_id
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



@app.command("list-analytics")
def list_analytics(
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Argument(help="versionId"),
    start_time: str = typer.Option(None, "--start-time", help="Epoch milliseconds for the start time of the period of inter"),
    end_time: str = typer.Option(None, "--end-time", help="Epoch milliseconds for the end time of the period of interes"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Analytics of a Flow Version object."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/{version_id}/analytics"
    params = {}
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time
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



@app.command("list-interactions")
def list_interactions(
    flow_id: str = typer.Argument(help="flowId"),
    from_param: str = typer.Option(None, "--from", help="Epoch milliseconds for the start time of the period of inter"),
    to: str = typer.Option(None, "--to", help="Epoch milliseconds for the end time of the period of interes"),
    interaction_id: str = typer.Option(None, "--interaction-id", help="Interaction ID. In case only a certain interaction is needed"),
    tag_ids: str = typer.Option(None, "--tag-ids", help="Tags IDs. Comma-separated values of tag IDs"),
    current_page: str = typer.Option(None, "--current-page", help="index of the current page for pagination"),
    page_size: str = typer.Option(None, "--page-size", help="determines the number of records in a page"),
    version_id: str = typer.Option(None, "--version-id", help="Flow Version ID. Example: 64e6cddfb3abcc05186f5f06"),
    activity_diagram_id: str = typer.Option(None, "--activity-diagram-id", help="Activity Diagram ID. Use this if only interactions touching"),
    search: str = typer.Option(None, "--search", help="search for ani, dnis, or interactionId"),
    sort_order: str = typer.Option(None, "--sort-order", help="sortOrder for the response, asc or desc"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get all interactions of a flow across its versions."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/interactions"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if interaction_id is not None:
        params["interactionId"] = interaction_id
    if tag_ids is not None:
        params["tagIds"] = tag_ids
    if current_page is not None:
        params["currentPage"] = current_page
    if page_size is not None:
        params["pageSize"] = page_size
    if version_id is not None:
        params["versionId"] = version_id
    if activity_diagram_id is not None:
        params["activityDiagramId"] = activity_diagram_id
    if search is not None:
        params["search"] = search
    if sort_order is not None:
        params["sortOrder"] = sort_order
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


