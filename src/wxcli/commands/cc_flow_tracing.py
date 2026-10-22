import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_flow_store_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center: cc-flow-tracing.")


@app.command("show-interaction", short_help="Get interaction metadata of a Flow Version object.")
def show_interaction(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    version_id: str = typer.Argument(help="from: wxcli cc-flow-versions list"),
    interaction_id: str = typer.Argument(help="interactionId"),
    convert_ids: str = typer.Option(None, "--convert-ids", help="Converts process IDs to diagram IDs. Possible values: 'true', 'false'"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get interaction metadata of a Flow Version object.\n\n\b\nExample: wxcli cc-flow-tracing show-interaction PROJECT_ID FLOW_ID VERSION_ID INTERACTION_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/{version_id}/interaction/{interaction_id}"
    params = {}
    if convert_ids is not None:
        params["convertIds"] = convert_ids
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-traces", short_help="Get traces by interaction ID of a Flow Version object.")
def list_traces(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    version_id: str = typer.Argument(help="from: wxcli cc-flow-versions list"),
    interaction_id: str = typer.Argument(help="interactionId"),
    current_page: str = typer.Option(None, "--current-page", help="index of the current page for pagination"),
    page_size: str = typer.Option(None, "--page-size", help="determines the number of records in a page"),
    process_id: str = typer.Option(None, "--process-id", help="processId of the flow version"),
    doc_id: str = typer.Option(None, "--doc-id", help="document id of the flow trace"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (pageSize); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get traces by interaction ID of a Flow Version object.\n\n\b\nExample: wxcli cc-flow-tracing list-traces PROJECT_ID FLOW_ID VERSION_ID INTERACTION_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
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
    if limit > 0 and not all_pages and params.get("pageSize") is None:
        params["pageSize"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="items", remedies=("all", "offset"))
        else:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-traces-decrypted", short_help="Get traces by interaction ID of a Flow Version object.")
def list_traces_decrypted(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    version_id: str = typer.Argument(help="from: wxcli cc-flow-versions list"),
    interaction_id: str = typer.Argument(help="interactionId"),
    process_id: str = typer.Option(..., "--process-id", help="processId of the flow version"),
    doc_id: str = typer.Option(None, "--doc-id", help="document id of the flow trace"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get traces by interaction ID of a Flow Version object.\n\nNOTE: Returns DECRYPTED traces; --process-id is required (get it from the undecrypted traces or the interaction metadata).\n\n\b\nExample: wxcli cc-flow-tracing list-traces-decrypted PROJECT_ID FLOW_ID VERSION_ID INTERACTION_ID --process-id PROCESS_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
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



@app.command("show-analytics", short_help="Get Analytics of a Flow Version object.")
def show_analytics(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    version_id: str = typer.Argument(help="from: wxcli cc-flow-versions list"),
    start_time: str = typer.Option(None, "--start-time", help="Epoch milliseconds for the start time of the period of interest. Example: 1720639334000"),
    end_time: str = typer.Option(None, "--end-time", help="Epoch milliseconds for the end time of the period of interest. Example: 1720639434000"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Analytics of a Flow Version object.\n\n\b\nExample: wxcli cc-flow-tracing show-analytics PROJECT_ID FLOW_ID VERSION_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/{version_id}/analytics"
    params = {}
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-interactions", short_help="Get all interactions of a flow across its versions.")
def list_interactions(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    from_param: str = typer.Option(None, "--from", help="Epoch milliseconds for the start time of the period of interest. Example: 1720639334000"),
    to: str = typer.Option(None, "--to", help="Epoch milliseconds for the end time of the period of interest. Example: 1720639434000"),
    interaction_id: str = typer.Option(None, "--interaction-id", help="Interaction ID. In case only a certain interaction is needed. Example: 151ed5fb-7181-4103-aef2-b2974d24c3ef"),
    tag_ids: str = typer.Option(None, "--tag-ids", help="Tags IDs. Comma-separated values of tag IDs"),
    current_page: str = typer.Option(None, "--current-page", help="index of the current page for pagination"),
    page_size: str = typer.Option(None, "--page-size", help="determines the number of records in a page"),
    version_id: str = typer.Option(None, "--version-id", help="Flow Version ID. Example: 64e6cddfb3abcc05186f5f06"),
    activity_diagram_id: str = typer.Option(None, "--activity-diagram-id", help="Activity Diagram ID. Use this if only interactions touching a specific activity are needed. Example: 84cd6a2a-5b7c-425e-8b00-9d0bd792afe9"),
    search: str = typer.Option(None, "--search", help="search for ani, dnis, or interactionId"),
    sort_order: str = typer.Option(None, "--sort-order", help="sortOrder for the response, asc or desc"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (pageSize); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get all interactions of a flow across its versions.\n\n\b\nExample: wxcli cc-flow-tracing list-interactions PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
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
    if limit > 0 and not all_pages and params.get("pageSize") is None:
        params["pageSize"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="interactions"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="interactions", remedies=("all", "offset"))
        else:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("interactions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Interaction ID', 'interactionId'), ('Version', 'flowVersionId'), ('ANI', 'ani'), ('DNIS', 'dnis'), ('Start', 'startTime'), ('End', 'endTime')], limit=limit)


