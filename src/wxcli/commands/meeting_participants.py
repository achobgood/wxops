import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Meetings meeting-participants.")


@app.command("list", short_help="List Meeting Participants.")
def cmd_list(
    meeting_id: str = typer.Option(..., "--meeting-id", help="The unique identifier for the meeting. Please note that currently meeting ID of a scheduled [personal room](https://help.webex.com/en-us/article/nul0wut/Webex-Personal-Rooms-in-Webex-Meetings) meeting is not supported for this API."),
    breakout_session_id: str = typer.Option(None, "--breakout-session-id", help="The unique identifier for a breakout session which happened during an ended meeting instance. If the `breakoutSessionId` is specified, the operation returns participants who joined the breakout session. Only applies to ended meeting instances."),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Meetings start from the specified date and time(exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `meetingStartTimeFrom` is not specified, it equals `meetingStartTimeTo` minus 1 month; if `meetingStartTimeTo` is also not specified, the default value for..."),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="Meetings start before the specified date and time(exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `meetingStartTimeTo` is not specified, it equals the result of a comparison, `meetingStartTimeFrom` plus one month and the current time, and the result is the..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes, the admin may specify the email of a user in a site they manage and the API will return meeting participants of the meetings that are hosted by that user."),
    join_time_from: str = typer.Option(None, "--join-time-from", help="The time participants join a meeting starts from the specified date and time (inclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `joinTimeFrom` is not specified, it equals `joinTimeTo` minus 7 days."),
    join_time_to: str = typer.Option(None, "--join-time-to", help="The time participants join a meeting before the specified date and time (exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `joinTimeTo` is not specified, it equals `joinTimeFrom` plus 7 days. The interval between `joinTimeFrom` and `joinTimeTo` must be within..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Participants.\n\n\b\nExample: wxcli meeting-participants list --meeting-id MEETING_ID"""
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
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Email', 'email'), ('Joined', 'joinedTime'), ('State', 'state')], limit=limit)



_BODY_SKELETON_CREATE = '{"emails":["..."],"joinTimeFrom":"...","joinTimeTo":"..."}'

@app.command("create", short_help="Query Meeting Participants with Email.")
def create(
    meeting_id: str = typer.Option(..., "--meeting-id", help="The unique identifier for the meeting."),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Meetings start from the specified date and time(exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `meetingStartTimeFrom` is not specified, it equals `meetingStartTimeTo` minus 1 month; if `meetingStartTimeTo` is also not specified, the default value for..."),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="Meetings start before the specified date and time(exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `meetingStartTimeTo` is not specified, it equals the result of a comparison, `meetingStartTimeFrom` plus one month and the current time, and the result is the..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes, the admin may specify the email of a user in a site they manage and the API will return meeting participants of the meetings that are hosted by that user."),
    join_time_from: str = typer.Option(None, "--join-time-from", help="The time participants join a meeting starts from the specified date and time (inclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `joinTimeFrom` is not specified, it equals `joinTimeTo` minus 7 days."),
    join_time_to: str = typer.Option(None, "--join-time-to", help="The time participants join a meeting before the specified date and time (exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `joinTimeTo` is not specified, it equals `joinTimeFrom` plus 7 days. The interval between `joinTimeFrom` and `joinTimeTo` must be within..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Meeting Participants with Email.\n\n\b\nExample: wxcli meeting-participants create --meeting-id MEETING_ID\n\n\b\nExample --json-body: '{"emails":["..."],"joinTimeFrom":"...","joinTimeTo":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
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
        body = load_json_body(json_body)
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



@app.command("show", short_help="Get Meeting Participant Details.")
def show(
    participant_id: str = typer.Argument(help="from: wxcli meeting-participants list"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes, the admin may specify the email of a user in a site they manage and the API will return meeting participants of the meetings that are hosted by that user."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Participant Details.\n\n\b\nExample: wxcli meeting-participants show PARTICIPANT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/{participant_id}"
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



_BODY_SKELETON_UPDATE = '{"muted":true,"admit":true,"expel":true}'

@app.command("update", short_help="Update a Participant.")
def update(
    participant_id: str = typer.Argument(help="from: wxcli meeting-participants list"),
    muted: bool = typer.Option(None, "--muted/--no-muted", help="If `true`, participant is muted."),
    admit: bool = typer.Option(None, "--admit/--no-admit", help="If `true` the participant admit a participant in the lobby to the meeting. Has no effect if the participant is not in the lobby or when the value is set to `false`."),
    expel: bool = typer.Option(None, "--expel/--no-expel", help="If `true` the participant is expelled from the meeting."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Participant.\n\n\b\nExample: wxcli meeting-participants update PARTICIPANT_ID\n\n\b\nExample --json-body: '{"muted":true,"admit":true,"expel":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/{participant_id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": participant_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_ADMIT = '{"items":[{"participantId":"...","breakoutSessionId":"..."}]}'

@app.command("create-admit", short_help="Admit Participants.")
def create_admit(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Admit Participants.\n\n\b\nExample --json-body: '{"items":[{"participantId":"...","breakoutSessionId":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ADMIT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/admit"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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



_BODY_SKELETON_CREATE_CALLOUT = '{"address":"...","displayName":"...","meetingId":"...","meetingNumber":"...","addressType":"sipAddress","invitationCorrelationId":"..."}'

@app.command("create-callout", short_help="Call Out a SIP Participant.")
def create_callout(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier of the meeting to which the SIP participant is to be called out. Either `meetingId` or `meetingNumber` must be specified."),
    meeting_number: str = typer.Option(None, "--meeting-number", help="Number of the meeting to which the SIP participant is to be called out. Either `meetingId` or `meetingNumber` must be specified."),
    address: str = typer.Option(None, "--address", help="(required) SIP address of the invited SIP participant."),
    address_type: str = typer.Option(None, "--address-type", help="Choices: sipAddress"),
    invitation_correlation_id: str = typer.Option(None, "--invitation-correlation-id", help="An internal ID that is associated with the call-out invitation. Only UUIDs with hyphens are supported. The letters in the UUID must be in lowercase. A random UUID will be generated automatically if not specified."),
    display_name: str = typer.Option(None, "--display-name", help="(required) The display name of the invited SIP participant. The maximum length is 32 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Call Out a SIP Participant.\n\n\b\nExample: wxcli meeting-participants create-callout --address ADDRESS --display-name DISPLAY_NAME\n\n\b\nExample --json-body: '{"address":"...","displayName":"...","meetingId":"...","meetingNumber":"...","addressType":"sipAddress","invitationCorrelationId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CALLOUT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/callout"
    if json_body:
        body = load_json_body(json_body)
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



_BODY_SKELETON_CREATE_CANCEL_CALLOUT = '{"participantId":"..."}'

@app.command("create-cancel-callout", short_help="Cancel Calling Out a SIP Participant.")
def create_cancel_callout(
    participant_id: str = typer.Option(None, "--participant-id", help="(required) ID of the SIP participant on whom the callout is to be cancelled. It can be retrieved from the response of the \"Call Out a SIP Participant\" API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Cancel Calling Out a SIP Participant.\n\n\b\nExample: wxcli meeting-participants create-cancel-callout --participant-id PARTICIPANT_ID\n\n\b\nExample --json-body: '{"participantId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CANCEL_CALLOUT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingParticipants/cancelCallout"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        typer.echo("Cancelled.")
    else:
        emit(result, output=output, fields=fields)


