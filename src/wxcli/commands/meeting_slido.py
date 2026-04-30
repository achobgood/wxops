import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-slido.")


@app.command("list")
def cmd_list(
    session_org_id: str = typer.Option(None, "--session-org-id", help="Webex organization UUID."),
    session_id: str = typer.Option(None, "--session-id", help="Webex meeting instance ID (`{meetingSeriesId}_I_{conferenceI"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Compliance Events."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/slido/compliance/events"
    params = {}
    if session_org_id is not None:
        params["sessionOrgId"] = session_org_id
    if session_id is not None:
        params["sessionId"] = session_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
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


