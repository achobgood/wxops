import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_flow_store_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center: cc-flow-connectors.")


@app.command("show", short_help="getConnector.")
def show(
    project_id: str = typer.Argument(help="projectId"),
    connector_id: str = typer.Argument(help="from: wxcli cc-flow-connectors list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """getConnector.\n\n\b\nExample: wxcli cc-flow-connectors show PROJECT_ID CONNECTOR_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/connector/{connector_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list", short_help="findAllConnectors.")
def cmd_list(
    project_id: str = typer.Argument(help="projectId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """findAllConnectors.\n\nNOTE: the system-provisioned project answers 404; connectors are listed only for user-created projects (Plan 2 T3, host map).\n\n\b\nExample: wxcli cc-flow-connectors list PROJECT_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/connector"
    params = {}
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
    items = result.get("connectors", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type')], limit=limit)


