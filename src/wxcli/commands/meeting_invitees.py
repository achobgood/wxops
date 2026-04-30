import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-invitees.")


@app.command("list")
def cmd_list(
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the meeting for which invitees are bei"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    panelist: str = typer.Option(None, "--panelist", help="Filter invitees or attendees for webinars only. If `true`, r"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Invitees."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if host_email is not None:
        params["hostEmail"] = host_email
    if panelist is not None:
        params["panelist"] = panelist
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
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Email', 'email')], limit=limit)



@app.command("create")
def create(
    meeting_id: str = typer.Option(None, "--meeting-id", help="(required) Unique identifier for the meeting to which a person is being"),
    email: str = typer.Option(None, "--email", help="(required) Email address for meeting invitee."),
    display_name: str = typer.Option(None, "--display-name", help="Display name for meeting invitee. The maximum length of `dis"),
    co_host: bool = typer.Option(None, "--co-host/--no-co-host", help="Whether or not the invitee is a designated alternate host fo"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true`, send an email to the invitee."),
    panelist: bool = typer.Option(None, "--panelist/--no-panelist", help="If `true`, the invitee is a designated panelist for the even"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Meeting Invitee."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if meeting_id is not None:
            body["meetingId"] = meeting_id
        if email is not None:
            body["email"] = email
        if display_name is not None:
            body["displayName"] = display_name
        if co_host is not None:
            body["coHost"] = co_host
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
        if panelist is not None:
            body["panelist"] = panelist
        _missing = [f for f in ['meetingId', 'email'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-bulk-insert")
def create_bulk_insert(
    meeting_id: str = typer.Option(None, "--meeting-id", help="(required) Unique identifier for the meeting to which the people are be"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Meeting Invitees\n\nExample --json-body:\n  '{"meetingId":"...","hostEmail":"...","items":[{"email":"...","displayName":"...","coHost":"...","sendEmail":"...","panelist":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees/bulkInsert"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if meeting_id is not None:
            body["meetingId"] = meeting_id
        if host_email is not None:
            body["hostEmail"] = host_email
        _missing = [f for f in ['meetingId'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show")
def show(
    meeting_invitee_id: str = typer.Argument(help="meetingInviteeId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Invitee."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees/{meeting_invitee_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        result = api.session.rest_get(url, params=params)
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



@app.command("update")
def update(
    meeting_invitee_id: str = typer.Argument(help="meetingInviteeId"),
    email: str = typer.Option(None, "--email", help="Email address for meeting invitee."),
    display_name: str = typer.Option(None, "--display-name", help="Display name for meeting invitee. The maximum length of `dis"),
    co_host: bool = typer.Option(None, "--co-host/--no-co-host", help="Whether or not the invitee is a designated alternate host fo"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true`, send an email to the invitee."),
    panelist: bool = typer.Option(None, "--panelist/--no-panelist", help="If `true`, the invitee is a designated panelist for the even"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Meeting Invitee."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees/{meeting_invitee_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if email is not None:
            body["email"] = email
        if display_name is not None:
            body["displayName"] = display_name
        if co_host is not None:
            body["coHost"] = co_host
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
        if panelist is not None:
            body["panelist"] = panelist
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    meeting_invitee_id: str = typer.Argument(help="meetingInviteeId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help="If `true`, send an email to the invitee."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Invitee."""
    if not force:
        typer.confirm(f"Delete {meeting_invitee_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees/{meeting_invitee_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if send_email is not None:
        params["sendEmail"] = send_email
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {meeting_invitee_id}")


