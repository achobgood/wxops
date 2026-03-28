import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling meetings-summary-report.")


@app.command("list")
def cmd_list(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meeting usage repo"),
    service_type: str = typer.Option(None, "--service-type", help="Meeting usage report's service-type. If `serviceType` is spe"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time for meeting usage reports to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time for meeting usage reports to return, in"),
    max: str = typer.Option(None, "--max", help="Maximum number of meetings to include in the meetings usage"),
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
    if max is not None:
        params["max"] = max
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
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-attendees")
def list_attendees(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meeting attendee r"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time for the meeting attendee reports to r"),
    to: str = typer.Option(None, "--to", help="Ending date and time for the meeting attendee reports to ret"),
    max: str = typer.Option(None, "--max", help="Maximum number of meeting attendees to include in the meetin"),
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
    if max is not None:
        params["max"] = max
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
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


