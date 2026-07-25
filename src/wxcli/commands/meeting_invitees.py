import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-invitees.")


@app.command("list")
def cmd_list(
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the meeting for which invitees are being requested. The meeting can be a meeting series, a scheduled meeting, or a meeting instance which has ended or is ongoing. The meeting ID of a scheduled [personal..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will return meeting invitees that are hosted by that user."),
    panelist: str = typer.Option(None, "--panelist", help="Filter invitees or attendees for webinars only. If `true`, returns invitees. If `false`, returns attendees. If `null`, returns both invitees and attendees."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Email', 'email')], limit=limit)



_BODY_SKELETON_CREATE = '{"meetingId":"...","email":"...","displayName":"...","coHost":true,"hostEmail":"...","sendEmail":true,"panelist":true}'

@app.command("create")
def create(
    meeting_id: str = typer.Option(None, "--meeting-id", help="(required) Unique identifier for the meeting to which a person is being invited. This attribute only applies to meeting series and scheduled meeting. If it's a meeting series, the meeting invitee is invited to the entire meeting series; if it's a scheduled meeting, the meeting invitee is invited to this..."),
    email: str = typer.Option(None, "--email", help="(required) Email address for meeting invitee."),
    display_name: str = typer.Option(None, "--display-name", help="Display name for meeting invitee. The maximum length of `displayName` is 128 characters. In the Webex app, if the email has been associated with an existing Webex account, the display name associated with the Webex account will be used; otherwise, the `email` will be used as `displayName`. In a..."),
    co_host: bool = typer.Option(None, "--co-host/--no-co-host", help="Whether or not the invitee is a designated alternate host for the meeting. See [Add Alternate Hosts for Cisco Webex Meetings](https://help.webex.com/b5z6he/) for more details."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin on-behalf-of scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true`, send an email to the invitee."),
    panelist: bool = typer.Option(None, "--panelist/--no-panelist", help="If `true`, the invitee is a designated panelist for the event meeting."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Meeting Invitee\n\nExample --json-body:\n  '{"meetingId":"...","email":"...","displayName":"...","coHost":true,"hostEmail":"...","sendEmail":true,"panelist":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_BULK_INSERT = '{"meetingId":"...","hostEmail":"...","items":[{"email":"...","displayName":"...","coHost":"...","sendEmail":"...","panelist":"..."}]}'

@app.command("create-bulk-insert")
def create_bulk_insert(
    meeting_id: str = typer.Option(None, "--meeting-id", help="(required) Unique identifier for the meeting to which the people are being invited. This attribute only applies to meeting series and scheduled meetings. If it's a meeting series, the meeting invitees are invited to the entire meeting series; if it's a scheduled meeting, the meeting invitees are invited to..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin on-behalf-of scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Meeting Invitees\n\nExample --json-body:\n  '{"meetingId":"...","hostEmail":"...","items":[{"email":"...","displayName":"...","coHost":"...","sendEmail":"...","panelist":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK_INSERT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees/bulkInsert"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("show")
def show(
    meeting_invitee_id: str = typer.Argument(help="meetingInviteeId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting invitee that is hosted by that user."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"email":"...","displayName":"...","coHost":true,"hostEmail":"...","sendEmail":true,"panelist":true}'

@app.command("update")
def update(
    meeting_invitee_id: str = typer.Argument(help="meetingInviteeId"),
    email: str = typer.Option(None, "--email", help="Email address for meeting invitee."),
    display_name: str = typer.Option(None, "--display-name", help="Display name for meeting invitee. The maximum length of `displayName` is 128 characters. In the Webex app, if the email has been associated with an existing Webex account, the display name associated with the Webex account will be used; otherwise, the `email` will be used as `displayName`. In a..."),
    co_host: bool = typer.Option(None, "--co-host/--no-co-host", help="Whether or not the invitee is a designated alternate host for the meeting. See [Add Alternate Hosts for Cisco Webex Meetings](https://help.webex.com/b5z6he/) for more details."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin on-behalf-of scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true`, send an email to the invitee."),
    panelist: bool = typer.Option(None, "--panelist/--no-panelist", help="If `true`, the invitee is a designated panelist for the event meeting."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Meeting Invitee\n\nExample --json-body:\n  '{"email":"...","displayName":"...","coHost":true,"hostEmail":"...","sendEmail":true,"panelist":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingInvitees/{meeting_invitee_id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("delete")
def delete(
    meeting_invitee_id: str = typer.Argument(help="meetingInviteeId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will delete a meeting invitee that is hosted by that user."),
    send_email: str = typer.Option(None, "--send-email", help="If `true`, send an email to the invitee."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Deleted: {meeting_invitee_id}")


