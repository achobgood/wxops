import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling recording-report.")


@app.command("list")
def cmd_list(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recording audit report summaries to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. Please note that the interval between `to` and `from` cannot exceed 90 days and the interval between the..."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for recording audit report summaries to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. Please note that the interval between `to` and `from` cannot exceed 90 days and the interval between the current..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will return recording audit report summaries of that user. If a special..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists recording audit report summaries from. If not specified, the API lists summary audit report for recordings from the user's preferred site. All available Webex sites and the preferred site of the user can be retrieved by `Get Site List` API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List of Recording Audit Report Summaries."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordingReport/accessSummary"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if host_email is not None:
        params["hostEmail"] = host_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-access-detail")
def list_access_detail(
    recording_id: str = typer.Option(..., "--recording-id", help="A unique identifier for the recording."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will return recording details of that user."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Recording Audit Report Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordingReport/accessDetail"
    params = {}
    if recording_id is not None:
        params["recordingId"] = recording_id
    if host_email is not None:
        params["hostEmail"] = host_email
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-meeting-archive-summaries")
def list_meeting_archive_summaries(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for meeting archive summaries to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. Please note that the interval between `to` and `from` cannot exceed 30 days."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for meeting archive summaries to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. Please note that the interval between `to` and `from` cannot exceed 30 days."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meeting archive summaries from. If not specified, the API lists meeting archive summaries for recordings from the user's preferred site. All available Webex sites and the preferred site of the user can be retrieved by `Get Site List` API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Archive Summaries."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordingReport/meetingArchiveSummaries"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if site_url is not None:
        params["siteUrl"] = site_url
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    archive_id: str = typer.Argument(help="archiveId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Archive Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordingReport/meetingArchives/{archive_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)


