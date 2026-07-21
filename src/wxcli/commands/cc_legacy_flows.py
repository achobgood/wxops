import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-legacy-flows.")


@app.command("list")
def cmd_list(
    flow_id: str = typer.Argument(help="flowId"),
    project_id: str = typer.Argument(help="projectId"),
    version: str = typer.Option(None, "--version", help="Version ID. Possible values are 'draft', 'latest' or version ID like '64b92c004ccd9f3d1c680709'. Defaulted to 'latest'."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Export a Flow or Subflow."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/flow-store/{org_id}/project/{project_id}/flows/{flow_id}:export"
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
    items = result.get("associatedChannels", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


