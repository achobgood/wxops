import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling teams.")


@app.command("list")
def cmd_list(
    max: str = typer.Option(None, "--max", help="Limit the maximum number of teams in the response."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Teams."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/teams"
    params = {}
    if max is not None:
        params["max"] = max
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
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("create")
def create(
    name: str = typer.Option(..., "--name", help="A user-friendly name for the team."),
    description: str = typer.Option(None, "--description", help="The teams description."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Team."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/teams"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
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
    team_id: str = typer.Argument(help="teamId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Team Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/teams/{team_id}"
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
    team_id: str = typer.Argument(help="teamId"),
    name: str = typer.Option(None, "--name", help="A user-friendly name for the team."),
    description: str = typer.Option(None, "--description", help="The teams description."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Team."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/teams/{team_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
    try:
        result = api.session.rest_put(url, json=body)
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
    team_id: str = typer.Argument(help="teamId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Team."""
    if not force:
        typer.confirm(f"Delete {team_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/teams/{team_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {team_id}")


