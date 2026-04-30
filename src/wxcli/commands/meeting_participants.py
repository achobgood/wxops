import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-participants.")


@app.command("list")
def cmd_list(
    meeting_id: str = typer.Option(..., "--meeting-id", help="The unique identifier for the meeting. Please note that curr"),
    breakout_session_id: str = typer.Option(None, "--breakout-session-id", help="The unique identifier for a breakout session which happened"),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Meetings start from the specified date and time(exclusive) i"),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="Meetings start before the specified date and time(exclusive)"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    join_time_from: str = typer.Option(None, "--join-time-from", help="The time participants join a meeting starts from the specifi"),
    join_time_to: str = typer.Option(None, "--join-time-to", help="The time participants join a meeting before the specified da"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Participants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if breakout_session_id is not None:
        params["breakoutSessionId"] = breakout_session_id
    if meeting_start_time_from is not None:
        params["meetingStartTimeFrom"] = meeting_start_time_from
    if meeting_start_time_to is not None:
        params["meetingStartTimeTo"] = meeting_start_time_to
    if host_email is not None:
        params["hostEmail"] = host_email
    if join_time_from is not None:
        params["joinTimeFrom"] = join_time_from
    if join_time_to is not None:
        params["joinTimeTo"] = join_time_to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Email', 'email'), ('Joined', 'joinedTime'), ('State', 'state')], limit=limit)



@app.command("create")
def create(
    meeting_id: str = typer.Option(..., "--meeting-id", help="The unique identifier for the meeting."),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Meetings start from the specified date and time(exclusive) i"),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="Meetings start before the specified date and time(exclusive)"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    join_time_from: str = typer.Option(None, "--join-time-from", help="The time participants join a meeting starts from the specifi"),
    join_time_to: str = typer.Option(None, "--join-time-to", help="The time participants join a meeting before the specified da"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Meeting Participants with Email\n\nExample --json-body:\n  '{"emails":["..."],"joinTimeFrom":"...","joinTimeTo":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/query"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if meeting_start_time_from is not None:
        params["meetingStartTimeFrom"] = meeting_start_time_from
    if meeting_start_time_to is not None:
        params["meetingStartTimeTo"] = meeting_start_time_to
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if join_time_from is not None:
            body["joinTimeFrom"] = join_time_from
        if join_time_to is not None:
            body["joinTimeTo"] = join_time_to
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
    participant_id: str = typer.Argument(help="participantId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Participant Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/{participant_id}"
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
    participant_id: str = typer.Argument(help="participantId"),
    muted: bool = typer.Option(None, "--muted/--no-muted", help="If `true`, participant is muted."),
    admit: bool = typer.Option(None, "--admit/--no-admit", help="If `true` the participant admit a participant in the lobby t"),
    expel: bool = typer.Option(None, "--expel/--no-expel", help="If `true` the participant is expelled from the meeting."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Participant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/{participant_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if muted is not None:
            body["muted"] = muted
        if admit is not None:
            body["admit"] = admit
        if expel is not None:
            body["expel"] = expel
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-admit")
def create_admit(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Admit Participants\n\nExample --json-body:\n  '{"items":[{"participantId":"...","breakoutSessionId":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/admit"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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



@app.command("create-callout")
def create_callout(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier of the meeting to which the SIP participan"),
    meeting_number: str = typer.Option(None, "--meeting-number", help="Number of the meeting to which the SIP participant is to be"),
    address: str = typer.Option(None, "--address", help="(required) SIP address of the invited SIP participant."),
    address_type: str = typer.Option(None, "--address-type", help="Choices: sipAddress"),
    invitation_correlation_id: str = typer.Option(None, "--invitation-correlation-id", help="An internal ID that is associated with the call-out invitati"),
    display_name: str = typer.Option(None, "--display-name", help="(required) The display name of the invited SIP participant. The maximum"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Call Out a SIP Participant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/callout"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if meeting_id is not None:
            body["meetingId"] = meeting_id
        if meeting_number is not None:
            body["meetingNumber"] = meeting_number
        if address is not None:
            body["address"] = address
        if address_type is not None:
            body["addressType"] = address_type
        if invitation_correlation_id is not None:
            body["invitationCorrelationId"] = invitation_correlation_id
        if display_name is not None:
            body["displayName"] = display_name
        _missing = [f for f in ['address', 'displayName'] if f not in body or body[f] is None]
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



@app.command("create-cancel-callout")
def create_cancel_callout(
    participant_id: str = typer.Option(None, "--participant-id", help="(required) ID of the SIP participant on whom the callout is to be cance"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Cancel Calling Out a SIP Participant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/cancelCallout"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if participant_id is not None:
            body["participantId"] = participant_id
        _missing = [f for f in ['participantId'] if f not in body or body[f] is None]
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


