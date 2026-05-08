import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id, get_cc_org_id, get_fs_base_url, get_fs_project_id


app = typer.Typer(help="Manage WxCC Flow Store fs-flow-versions.")


@app.command("show")
def show(
    flow_id: str = typer.Argument(help="flowId"),
    page: str = typer.Option(None, "--page", help=""),
    size: str = typer.Option(None, "--size", help=""),
    sort: str = typer.Option(None, "--sort", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getPublishedFlowVersions."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions"
    params = {}
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if sort is not None:
        params["sort"] = sort
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



@app.command("show-versions-flows")
def show_versions_flows(
    flow_id: str = typer.Argument(help="flowId"),
    version_id: str = typer.Argument(help="versionId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getFlowVersionById."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/{version_id}"
    try:
        result = api.session.rest_get(url)
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



@app.command("show-latest")
def show_latest(
    flow_id: str = typer.Argument(help="flowId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getLatestFlowVersion."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/latest"
    try:
        result = api.session.rest_get(url)
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



@app.command("show-draft")
def show_draft(
    flow_id: str = typer.Argument(help="flowId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getLatestFlowDraftVersion."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/versions/draft"
    try:
        result = api.session.rest_get(url)
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



@app.command("show-versions-flows-1")
def show_versions_flows_1(
    page: str = typer.Option(None, "--page", help=""),
    size: str = typer.Option(None, "--size", help=""),
    search_by: str = typer.Option(None, "--search-by", help=""),
    sort: str = typer.Option(None, "--sort", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getAllFlowVersions."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{projectId}/flows/versions"
    params = {}
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if search_by is not None:
        params["searchBy"] = search_by
    if sort is not None:
        params["sort"] = sort
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



@app.command("show-all-latest")
def show_all_latest(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """findAllLatestFlowVersions."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/versions/all-latest"
    try:
        result = api.session.rest_get(url)
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


