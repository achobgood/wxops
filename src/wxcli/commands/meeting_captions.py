import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-captions.")


@app.command("list")
def cmd_list(
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the [meeting instance](/docs/meetings#meeting-series-scheduled-meetings-and-meeting-instances) which the closed captions belong to. This parameter only applies to ended meeting instances. It does not apply to meeting series, scheduled meetings or scheduled [personal..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Closed Captions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingClosedCaptions"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-snippets")
def list_snippets(
    closed_caption_id: str = typer.Argument(help="closedCaptionId"),
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the [meeting instance](/docs/meetings#meeting-series-scheduled-meetings-and-meeting-instances) which the closed caption snippets belong to. This parameter only applies to ended meeting instances. It does not apply to meeting series, scheduled meetings or scheduled [personal..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Closed Caption Snippets."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingClosedCaptions/{closed_caption_id}/snippets"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-download")
def list_download(
    closed_caption_id: str = typer.Argument(help="closedCaptionId"),
    format_param: str = typer.Option(None, "--format", help="Choices: vtt, txt"),
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the [meeting instance](/docs/meetings#meeting-series-scheduled-meetings-and-meeting-instances) which the closed caption snippets belong to. This parameter only applies to meeting instances in the `ended` state. It does not apply to meeting series, scheduled meetings or..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Download Meeting Closed Caption Snippets."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingClosedCaptions/{closed_caption_id}/download"
    params = {}
    if format_param is not None:
        params["format"] = format_param
    if meeting_id is not None:
        params["meetingId"] = meeting_id
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


