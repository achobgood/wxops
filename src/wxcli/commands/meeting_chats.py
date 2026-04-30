import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-chats.")


@app.command("list")
def cmd_list(
    meeting_id: str = typer.Option(..., "--meeting-id", help="A unique identifier for the [meeting instance](/docs/meeting"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Chats."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/postMeetingChats"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["offset"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("delete")
def delete(
    meeting_id: str = typer.Option(..., "--meeting-id", help="A unique identifier for the [meeting instance](/docs/meeting"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Meeting Chats."""
    if not force:
        typer.confirm("Delete this resource?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/postMeetingChats"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo("Deleted.")


