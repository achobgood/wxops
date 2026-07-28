import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-summaries.")


@app.command("list", short_help="Get Summary by Meeting ID.")
def cmd_list(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the [meeting instance](/docs/meetings#meeting-series-scheduled-meetings-and-meeting-instances) to which the summary belongs. Please note that currently the meeting ID of a meeting series, a scheduled meeting, an in-progress meeting instance, or a scheduled personal room..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Summary by Meeting ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingSummaries"
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Meeting ID', 'meetingId'), ('Status', 'status')], limit=limit)



@app.command("list-meeting-summaries", short_help="Get Summary For Compliance Officer.")
def list_meeting_summaries(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the [meeting instance](/docs/meetings#meeting-series-scheduled-meetings-and-meeting-instances) to which the summary belongs. Please note that currently the meeting ID of a meeting series, a scheduled meeting, an in-progress meeting instance, or a scheduled personal room..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Summary For Compliance Officer."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetingSummaries"
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Meeting ID', 'meetingId'), ('Status', 'status')], limit=limit)



@app.command("delete", short_help="Delete a Summary.")
def delete(
    summary_id: str = typer.Argument(help="UUID, from: wxcli meeting-summaries list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Summary.\n\n\b\nExample: wxcli meeting-summaries delete SUMMARY_ID"""
    if not force:
        typer.confirm(f"Delete {summary_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingSummaries/{summary_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {summary_id}")
    else:
        emit({"status": "deleted", "id": summary_id}, output=output, fields=fields)


