import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling recording-report.")


@app.command("list", short_help="List of Recording Audit Report Summaries.")
def cmd_list(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recording audit report summaries to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. Please note that the interval between `to` and `from` cannot exceed 90 days and the interval between the..."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for recording audit report summaries to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. Please note that the interval between `to` and `from` cannot exceed 90 days and the interval between the current..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will return recording audit report summaries of that user. If a special..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists recording audit report summaries from. If not specified, the API lists summary audit report for recordings from the user's preferred site. All available Webex sites and the preferred site of the user can be retrieved by `Get Site List` API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Recording ID', 'recordingId'), ('Topic', 'topic'), ('Time Recorded', 'timeRecorded'), ('Site URL', 'siteUrl'), ('Host Email', 'hostEmail')], limit=limit)



@app.command("list-access-detail", short_help="Get Recording Audit Report Details.")
def list_access_detail(
    recording_id: str = typer.Option(..., "--recording-id", help="A unique identifier for the recording."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will return recording details of that user."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Recording Audit Report Details.\n\n\b\nExample: wxcli recording-report list-access-detail --recording-id RECORDING_ID"""
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
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Recording ID', 'recordingId'), ('Name', 'name'), ('Topic', 'topic'), ('Email', 'email'), ('Access Time', 'accessTime')], limit=limit)



@app.command("list-meeting-archive-summaries", short_help="List Meeting Archive Summaries.")
def list_meeting_archive_summaries(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for meeting archive summaries to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. Please note that the interval between `to` and `from` cannot exceed 30 days."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for meeting archive summaries to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. Please note that the interval between `to` and `from` cannot exceed 30 days."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meeting archive summaries from. If not specified, the API lists meeting archive summaries for recordings from the user's preferred site. All available Webex sites and the preferred site of the user can be retrieved by `Get Site List` API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Archive ID', 'archiveId'), ('Title', 'title'), ('Service Type', 'serviceType'), ('Create Time', 'createTime')], limit=limit)



@app.command("show", short_help="Get Meeting Archive Details.")
def show(
    archive_id: str = typer.Argument(help="archiveId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Archive Details.\n\n\b\nExample: wxcli recording-report show ARCHIVE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordingReport/meetingArchives/{archive_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


