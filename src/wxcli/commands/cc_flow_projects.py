import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_flow_store_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center: cc-flow-projects.")


@app.command("show-user-preferences", short_help="Get user preferences for a project.")
def show_user_preferences(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get user preferences for a project."""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/userPreferences"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show", short_help="findProject.")
def show(
    project_id: str = typer.Argument(help="projectId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """findProject.\n\nNOTE: the system-provisioned project (the projectId from show-user-preferences) answers 404 "Project with id ... not found"; this works on user-created projects (Plan 2 T3, host map).\n\n\b\nExample: wxcli cc-flow-projects show PROJECT_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list", short_help="findAll.")
def cmd_list(
    page: str = typer.Option(None, "--page", help=""),
    size: str = typer.Option(None, "--size", help=""),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (size); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """findAll."""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project"
    params = {}
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if limit > 0 and not all_pages and params.get("size") is None:
        params["size"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="projects", size_param="size"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="projects", size_param="size", remedies=("all", "offset"))
        else:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("projects", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Default', 'default'), ('Created By', 'createdBy')], limit=limit)



@app.command("list-resource-collections", short_help="Get list of RCs for current user with simplified permission flags.")
def list_resource_collections(
    page: str = typer.Option(None, "--page", help="Defines the number of the displayed page. The page number starts from 0."),
    size: str = typer.Option(None, "--size", help="Defines the number of items to be displayed on a page."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (size); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get list of RCs for current user with simplified permission flags."""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/resource-collections"
    params = {}
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if limit > 0 and not all_pages and params.get("size") is None:
        params["size"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items", size_param="size"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="items", size_param="size", remedies=("all", "offset"))
        else:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


