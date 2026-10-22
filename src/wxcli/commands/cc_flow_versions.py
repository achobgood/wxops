import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_flow_store_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center: cc-flow-versions.")


@app.command("list", short_help="getPublishedFlowVersions.")
def cmd_list(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    page: str = typer.Option(None, "--page", help=""),
    size: str = typer.Option(None, "--size", help=""),
    sort: str = typer.Option(None, "--sort", help="Sets the `sort` query param (sort order)"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (size); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """getPublishedFlowVersions.\n\n\b\nExample: wxcli cc-flow-versions list PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions"
    params = {}
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if sort is not None:
        params["sort"] = sort
    if limit > 0 and not all_pages and params.get("size") is None:
        params["size"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="versions", size_param="size"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="versions", size_param="size", remedies=("all", "offset"))
        else:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("versions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Version ID', 'id'), ('Version', 'version'), ('Tag', 'tag'), ('Published', 'publishedDate'), ('Created By', 'createdBy')], limit=limit)



@app.command("show", short_help="getFlowVersionById.")
def show(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    version_id: str = typer.Argument(help="from: wxcli cc-flow-versions list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """getFlowVersionById.\n\n\b\nExample: wxcli cc-flow-versions show PROJECT_ID FLOW_ID VERSION_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/{version_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-latest", short_help="getLatestFlowVersion.")
def show_latest(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """getLatestFlowVersion.\n\n\b\nExample: wxcli cc-flow-versions show-latest PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/latest"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-draft", short_help="getLatestFlowDraftVersion.")
def show_draft(
    project_id: str = typer.Argument(help="projectId"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """getLatestFlowDraftVersion.\n\n\b\nExample: wxcli cc-flow-versions show-draft PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/draft"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-all", short_help="getAllFlowVersions.")
def list_all(
    project_id: str = typer.Argument(help="projectId"),
    page: str = typer.Option(None, "--page", help=""),
    size: str = typer.Option(None, "--size", help=""),
    search_by: str = typer.Option(None, "--search-by", help="Filter (sets the `searchBy` query param)"),
    sort: str = typer.Option(None, "--sort", help="Sets the `sort` query param (sort order)"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (size); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """getAllFlowVersions.\n\n\b\nExample: wxcli cc-flow-versions list-all PROJECT_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/versions"
    params = {}
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if search_by is not None:
        params["searchBy"] = search_by
    if sort is not None:
        params["sort"] = sort
    if limit > 0 and not all_pages and params.get("size") is None:
        params["size"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="versions", size_param="size"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="versions", size_param="size", remedies=("all", "offset"))
        else:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("versions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Version ID', 'id'), ('Name', 'name'), ('Version', 'version'), ('Type', 'flowType'), ('Created', 'createdDate')], limit=limit)



@app.command("list-all-latest", short_help="findAllLatestFlowVersions.")
def list_all_latest(
    project_id: str = typer.Argument(help="projectId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """findAllLatestFlowVersions.\n\n\b\nExample: wxcli cc-flow-versions list-all-latest PROJECT_ID"""
    typer.echo("Warning: 500s org-wide when never-published flows exist; fall back to paged 'wxcli cc-flow-versions list-all'", err=True)
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/versions/all-latest"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


