import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling hot-desk.")


@app.command("list", short_help="List Sessions.")
def cmd_list(
    person_id: str = typer.Option(None, "--person-id", help="List sessions for this person."),
    workspace_id: str = typer.Option(None, "--workspace-id", help="List sessions for this workspace."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Session ID', 'sessionId'), ('Workspace ID', 'workspaceId'), ('Person ID', 'personId'), ('Booking Start Time', 'bookingStartTime'), ('Booking End Time', 'bookingEndTime')], limit=limit)



@app.command("delete", short_help="Delete Session.")
def delete(
    session_id: str = typer.Argument(help="Webex HDSESSION id, from: wxcli hot-desk list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Session.\n\n\b\nExample: wxcli hot-desk delete SESSION_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {session_id}?", abort=True)
    url = f"https://webexapis.com/v1/hotdesk/sessions/{session_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {session_id}")
    else:
        emit({"status": "deleted", "id": session_id}, output=output, fields=fields)


