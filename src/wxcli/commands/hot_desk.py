import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling hot-desk.")


@app.command("list")
def cmd_list(
    person_id: str = typer.Option(None, "--person-id", help="List sessions for this person."),
    workspace_id: str = typer.Option(None, "--workspace-id", help="List sessions for this workspace."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Sessions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hotdesk/sessions"
    params = {}
    if person_id is not None:
        params["personId"] = person_id
    if workspace_id is not None:
        params["workspaceId"] = workspace_id
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
    items = result.get("sessions", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("delete")
def delete(
    session_id: str = typer.Argument(help="sessionId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Session."""
    if not force:
        typer.confirm(f"Delete {session_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hotdesk/sessions/{session_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {session_id}")


