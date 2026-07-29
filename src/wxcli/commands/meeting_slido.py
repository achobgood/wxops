import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-slido.")


@app.command("list", short_help="List Compliance Events.")
def cmd_list(
    session_org_id: str = typer.Option(..., "--session-org-id", help="Webex organization UUID."),
    session_id: str = typer.Option(..., "--session-id", help="Webex meeting instance ID (`{meetingSeriesId}_I_{conferenceId}`)."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Compliance Events.\n\n\b\nExample: wxcli meeting-slido list --session-org-id SESSION_ORG_ID --session-id SESSION_ID"""
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
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Session ID', 'sessionId'), ('Created At Ms', 'createdAtMs'), ('Session Org ID', 'sessionOrgId'), ('User ID', 'userId')], limit=limit)


