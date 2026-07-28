import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-reports.")


@app.command("list", short_help="List Meeting Usage Reports.")
def cmd_list(
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site which the API lists meeting usage reports from. All available Webex sites can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    service_type: str = typer.Option(None, "--service-type", help="Meeting usage report's service-type. If `serviceType` is specified, the API filters meeting usage reports by service-type. If `serviceType` is not specified, the API returns meeting usage reports by `MeetingCenter` by default. Valid values: + `MeetingCenter` + `EventCenter` + `SupportCenter` +..."),
    from_param: str = typer.Option(None, "--from", help="Starting date and time for meeting usage reports to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. The interval between `to` and `from` cannot exceed 30 days and `from` cannot be earlier than 90 days ago."),
    to: str = typer.Option(None, "--to", help="Ending date and time for meeting usage reports to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. The interval between `to` and `from` cannot exceed 30 days."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Usage Reports.\n\n\b\nExample: wxcli meeting-reports list --site-url SITE_URL"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingReports/usage"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    if service_type is not None:
        params["serviceType"] = service_type
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Meeting ID', 'meetingId'), ('Host Display Name', 'hostDisplayName'), ('Meeting Number', 'meetingNumber'), ('Meeting Title', 'meetingTitle'), ('Start', 'start')], limit=limit)



@app.command("list-attendees", short_help="List Meeting Attendee Reports.")
def list_attendees(
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site which the API lists meeting attendee reports from. All available Webex sites can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    from_param: str = typer.Option(None, "--from", help="Starting date and time for the meeting attendee reports to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. The interval between `to` and `from` cannot exceed 30 days and `from` cannot be earlier than 90 days ago."),
    to: str = typer.Option(None, "--to", help="Ending date and time for the meeting attendee reports to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. The interval between `to` and `from` cannot exceed 30 days."),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Meeting ID for the meeting attendee reports to return. If specified, return meeting attendee reports of the specified meeting; otherwise, return meeting attendee reports of all meetings. Currently, only ended meeting instance IDs are supported. IDs of meeting series, scheduled meetings or personal..."),
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number for the meeting attendee reports to return. If specified, return meeting attendee reports of the specified meeting; otherwise, return meeting attendee reports of all meetings."),
    meeting_title: str = typer.Option(None, "--meeting-title", help="Meeting title for the meeting attendee reports to return. If specified, return meeting attendee reports of the specified meeting; otherwise, return meeting attendee reports of all meetings."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Attendee Reports.\n\n\b\nExample: wxcli meeting-reports list-attendees --site-url SITE_URL"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingReports/attendees"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if meeting_number is not None:
        params["meetingNumber"] = meeting_number
    if meeting_title is not None:
        params["meetingTitle"] = meeting_title
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Meeting ID', 'meetingId'), ('Display Name', 'displayName'), ('Meeting Number', 'meetingNumber'), ('Meeting Title', 'meetingTitle'), ('Email', 'email')], limit=limit)


