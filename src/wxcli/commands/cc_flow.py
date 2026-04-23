import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-flow.")


@app.command("list")
def cmd_list(
    project_id: str = typer.Argument(help="projectId"),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    ids: str = typer.Option(None, "--ids", help="Filters results based on a comma-separated list of flow IDs."),
    page: str = typer.Option(None, "--page", help="Defines the number of the displayed page. The page number st"),
    partial_name_search: str = typer.Option(None, "--partial-name-search", help="Performs a partial string match on the name of the flow. If"),
    size: str = typer.Option(None, "--size", help="Defines the number of items to be displayed on a page. If th"),
    include_pagination: str = typer.Option(None, "--include-pagination", help="If set to to true then a different paginated response object"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Flows or Subflows."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/flow-store/{org_id}/project/{project_id}/flows"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if ids is not None:
        params["ids"] = ids
    if page is not None:
        params["page"] = page
    if partial_name_search is not None:
        params["partialNameSearch"] = partial_name_search
    if size is not None:
        params["size"] = size
    if include_pagination is not None:
        params["includePagination"] = include_pagination
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("export")
def export(
    flow_id: str = typer.Argument(help="flowId"),
    project_id: str = typer.Argument(help="projectId"),
    version: str = typer.Option(None, "--version", help="Version ID. Possible values are 'draft', 'latest' or version"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Export a Flow or Subflow."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/flow-store/{org_id}/project/{project_id}/flows/{flow_id}:export"
    params = {}
    if version is not None:
        params["version"] = version
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("runtimeVariables", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("publish")
def publish(
    flow_id: str = typer.Argument(help="flowId"),
    project_id: str = typer.Argument(help="projectId"),
    comment: str = typer.Option(None, "--comment", help="A comment to provide context on publishing the flow."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Publish a Flow or Subflow\n\nExample --json-body:\n  '{"comment":"...","tagIds":["..."]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/flow-store/{org_id}/project/{project_id}/flows/{flow_id}:publish"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if comment is not None:
            body["comment"] = comment
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


