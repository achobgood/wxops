import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling groups.")


@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Searches the group by `displayName` with an operator and a v"),
    attributes: str = typer.Option(None, "--attributes", help="The attributes to return."),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort the results based by group `displayName`."),
    sort_order: str = typer.Option(None, "--sort-order", help="Sort results alphabetically by group display name, in ascend"),
    include_members: str = typer.Option(None, "--include-members", help="Optionally return group members in the response. The maximum"),
    start_index: str = typer.Option(None, "--start-index", help="The index to start for group pagination."),
    count: str = typer.Option(None, "--count", help="Specifies the desired number of search results per page."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List and Search Groups."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_order is not None:
        params["sortOrder"] = sort_order
    if include_members is not None:
        params["includeMembers"] = include_members
    if start_index is not None:
        params["startIndex"] = start_index
    if count is not None:
        params["count"] = count
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("groups", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Member Count', 'memberSize')], limit=limit)



@app.command("create")
def create(
    display_name: str = typer.Option(..., "--display-name", help="A human-readable name for the Group."),
    external_id: str = typer.Option(None, "--external-id", help="An identifier for the resource as defined by the provisionin"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if display_name is not None:
            body["displayName"] = display_name
        if external_id is not None:
            body["externalId"] = external_id
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show")
def show(
    group_id: str = typer.Argument(help="groupId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Group Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups/{group_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update")
def update(
    group_id: str = typer.Argument(help="groupId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups/{group_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    group_id: str = typer.Argument(help="groupId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Group."""
    if not force:
        typer.confirm(f"Delete {group_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups/{group_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {group_id}")



@app.command("list-members")
def list_members(
    group_id: str = typer.Argument(help="groupId"),
    start_index: str = typer.Option(None, "--start-index", help="The index to start for group pagination."),
    count: str = typer.Option(None, "--count", help="Non-negative integer that specifies the desired number of se"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Group Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/groups/{group_id}/members"
    params = {}
    if start_index is not None:
        params["startIndex"] = start_index
    if count is not None:
        params["count"] = count
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("members", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Member Count', 'memberSize')], limit=limit)


