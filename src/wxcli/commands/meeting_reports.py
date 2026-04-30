import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-reports.")


@app.command("list")
def cmd_list(
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site which the API lists meeting usage repo"),
    service_type: str = typer.Option(None, "--service-type", help="Meeting usage report's service-type. If `serviceType` is spe"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time for meeting usage reports to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time for meeting usage reports to return, in"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Usage Reports."""
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
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-attendees")
def list_attendees(
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site which the API lists meeting attendee r"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time for the meeting attendee reports to r"),
    to: str = typer.Option(None, "--to", help="Ending date and time for the meeting attendee reports to ret"),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Meeting ID for the meeting attendee reports to return. If sp"),
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number for the meeting attendee reports to return. I"),
    meeting_title: str = typer.Option(None, "--meeting-title", help="Meeting title for the meeting attendee reports to return. If"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Attendee Reports."""
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
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


