import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-chats.")


@app.command("list", short_help="List Meeting Chats.")
def cmd_list(
    meeting_id: str = typer.Option(..., "--meeting-id", help="A unique identifier for the [meeting instance](/docs/meetings#meeting-series-scheduled-meetings-and-meeting-instances) to which the chats belong. The meeting ID of a scheduled [personal room](https://help.webex.com/en-us/article/nul0wut/Webex-Personal-Rooms-in-Webex-Meetings) meeting is not..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Chats.\n\n\b\nExample: wxcli meeting-chats list --meeting-id MEETING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/postMeetingChats"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["offset"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Chat Time', 'chatTime'), ('Text', 'text'), ('Meeting ID', 'meetingId'), ('Type', 'type')], limit=limit)



@app.command("delete", short_help="Delete Meeting Chats.")
def delete(
    meeting_id: str = typer.Option(..., "--meeting-id", help="A unique identifier for the [meeting instance](/docs/meetings#meeting-series-scheduled-meetings-and-meeting-instances) to which the chats belong. Meeting IDs of a scheduled [personal room](https://help.webex.com/en-us/article/nul0wut/Webex-Personal-Rooms-in-Webex-Meetings) meeting are not supported."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Meeting Chats.\n\n\b\nExample: wxcli meeting-chats delete --meeting-id MEETING_ID"""
    if not force:
        typer.confirm("Delete this resource?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/postMeetingChats"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo("Deleted.")
    else:
        emit({"status": "deleted"}, output=output, fields=fields)


