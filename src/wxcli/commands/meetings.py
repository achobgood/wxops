import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meetings.")


@app.command("show")
def show(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting By an Admin."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetings/{meeting_id}"
    params = {}
    if current is not None:
        params["current"] = current
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("list")
def cmd_list(
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number for the meeting objects being requested. `mee"),
    web_link: str = typer.Option(None, "--web-link", help="URL encoded link to information page for the meeting objects"),
    current: str = typer.Option(None, "--current", help="Flag identifying to retrieve the current scheduled meeting o"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meetings By an Admin."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetings"
    params = {}
    if meeting_number is not None:
        params["meetingNumber"] = meeting_number
    if web_link is not None:
        params["webLink"] = web_link
    if current is not None:
        params["current"] = current
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
            if "max" not in params:
                params["max"] = 1000
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("list-meetings")
def list_meetings(
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number for the meeting objects being requested. `mee"),
    web_link: str = typer.Option(None, "--web-link", help="URL encoded link to information page for the meeting objects"),
    room_id: str = typer.Option(None, "--room-id", help="Associated Webex space ID for the meeting objects being requ"),
    meeting_series_id: str = typer.Option(None, "--meeting-series-id", help="Unique identifier for the meeting series. The meeting ID of"),
    from_param: str = typer.Option(None, "--from", help="Start date and time (inclusive) for the range for which meet"),
    to: str = typer.Option(None, "--to", help="End date and time (exclusive) for the range for which meetin"),
    meeting_type: str = typer.Option(None, "--meeting-type", help="Choices: meetingSeries, scheduledMeeting, meeting"),
    state: str = typer.Option(None, "--state", help="Choices: active, scheduled, ready, lobby, inProgress, ended, missed, expired"),
    scheduled_type: str = typer.Option(None, "--scheduled-type", help="Choices: meeting, webinar, personalRoomMeeting"),
    is_modified: str = typer.Option(None, "--is-modified", help="Flag identifying whether a meeting has been modified. Only a"),
    has_chat: str = typer.Option(None, "--has-chat", help="Flag identifying whether a meeting has a chat log. Only appl"),
    has_recording: str = typer.Option(None, "--has-recording", help="Flag identifying meetings which have been recorded. Only app"),
    has_transcription: str = typer.Option(None, "--has-transcription", help="Flag identifying meetings with transcripts. Only applies to"),
    has_summary: str = typer.Option(None, "--has-summary", help="Flag identifying meetings with summaries. Only applies to en"),
    has_closed_caption: str = typer.Option(None, "--has-closed-caption", help="Flag identifying meetings with closed captions. Only applies"),
    has_polls: str = typer.Option(None, "--has-polls", help="Flag identifying meetings with polls. Only applies to ended"),
    has_qa: str = typer.Option(None, "--has-qa", help="Flag identifying meetings with Q&A. Only applies to ended me"),
    has_slido: str = typer.Option(None, "--has-slido", help="Flag identifying meetings with Slido interactions. Only appl"),
    current: str = typer.Option(None, "--current", help="Flag identifying to retrieve the current scheduled meeting o"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meetings from. If"),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key created by an integration application. This par"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meetings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings"
    params = {}
    if meeting_number is not None:
        params["meetingNumber"] = meeting_number
    if web_link is not None:
        params["webLink"] = web_link
    if room_id is not None:
        params["roomId"] = room_id
    if meeting_series_id is not None:
        params["meetingSeriesId"] = meeting_series_id
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if meeting_type is not None:
        params["meetingType"] = meeting_type
    if state is not None:
        params["state"] = state
    if scheduled_type is not None:
        params["scheduledType"] = scheduled_type
    if is_modified is not None:
        params["isModified"] = is_modified
    if has_chat is not None:
        params["hasChat"] = has_chat
    if has_recording is not None:
        params["hasRecording"] = has_recording
    if has_transcription is not None:
        params["hasTranscription"] = has_transcription
    if has_summary is not None:
        params["hasSummary"] = has_summary
    if has_closed_caption is not None:
        params["hasClosedCaption"] = has_closed_caption
    if has_polls is not None:
        params["hasPolls"] = has_polls
    if has_qa is not None:
        params["hasQA"] = has_qa
    if has_slido is not None:
        params["hasSlido"] = has_slido
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if integration_tag is not None:
        params["integrationTag"] = integration_tag
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create")
def create(
    adhoc: bool = typer.Option(None, "--adhoc/--no-adhoc", help="Whether or not to create an ad-hoc meeting for the room spec"),
    room_id: str = typer.Option(None, "--room-id", help="Unique identifier for the Webex space which the meeting is t"),
    template_id: str = typer.Option(None, "--template-id", help="Unique identifier for meeting template. Please note that `st"),
    title: str = typer.Option(None, "--title", help="(required) Meeting title. The title can be a maximum of 128 characters"),
    agenda: str = typer.Option(None, "--agenda", help="Meeting agenda. The agenda can be a maximum of 1300 characte"),
    password: str = typer.Option(None, "--password", help="Meeting password. Must conform to the site's password comple"),
    start: str = typer.Option(None, "--start", help="(required) Date and time for the start of meeting in any [ISO 8601](htt"),
    end: str = typer.Option(None, "--end", help="(required) Date and time for the end of meeting in any [ISO 8601](https"),
    timezone: str = typer.Option(None, "--timezone", help="[Time zone](https://en.wikipedia.org/wiki/List_of_tz_databas"),
    recurrence: str = typer.Option(None, "--recurrence", help="Meeting series recurrence rule (conforming with [RFC 2445](h"),
    enabled_auto_record_meeting: bool = typer.Option(None, "--enabled-auto-record-meeting/--no-enabled-auto-record-meeting", help="Whether or not meeting is recorded automatically."),
    allow_any_user_to_be_co_host: bool = typer.Option(None, "--allow-any-user-to-be-co-host/--no-allow-any-user-to-be-co-host", help="Whether or not to allow any attendee with a host account on"),
    enabled_join_before_host: bool = typer.Option(None, "--enabled-join-before-host/--no-enabled-join-before-host", help="Whether or not to allow any attendee to join the meeting bef"),
    enable_connect_audio_before_host: bool = typer.Option(None, "--enable-connect-audio-before-host/--no-enable-connect-audio-before-host", help="Whether or not to allow any attendee to connect audio in the"),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help="Number of minutes an attendee can join the meeting before th"),
    exclude_password: bool = typer.Option(None, "--exclude-password/--no-exclude-password", help="Whether or not to exclude the meeting password from the emai"),
    public_meeting: bool = typer.Option(None, "--public-meeting/--no-public-meeting", help="Whether or not to allow the meeting to be listed on the publ"),
    reminder_time: str = typer.Option(None, "--reminder-time", help="The number of minutes before the meeting begins, that an ema"),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help="Choices: allowJoin, allowJoinWithLobby, blockFromJoin"),
    session_type_id: str = typer.Option(None, "--session-type-id", help="Unique identifier for a meeting session type for the user. T"),
    scheduled_type: str = typer.Option(None, "--scheduled-type", help="Choices: meeting, webinar, personalRoomMeeting"),
    enabled_webcast_view: bool = typer.Option(None, "--enabled-webcast-view/--no-enabled-webcast-view", help="Whether or not webcast view is enabled. This parameter is ig"),
    panelist_password: str = typer.Option(None, "--panelist-password", help="Password for panelists of a webinar meeting. Must conform to"),
    enable_automatic_lock: bool = typer.Option(None, "--enable-automatic-lock/--no-enable-automatic-lock", help="Whether or not to automatically lock the meeting after it st"),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help="The number of minutes after the meeting begins, for automati"),
    allow_first_user_to_be_co_host: bool = typer.Option(None, "--allow-first-user-to-be-co-host/--no-allow-first-user-to-be-co-host", help="Whether or not to allow the first attendee of the meeting wi"),
    allow_authenticated_devices: bool = typer.Option(None, "--allow-authenticated-devices/--no-allow-authenticated-devices", help="Whether or not to allow authenticated video devices in the m"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether or not to send emails to host and invitees. It is an"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the meeting is created on. If no"),
    enabled_breakout_sessions: bool = typer.Option(None, "--enabled-breakout-sessions/--no-enabled-breakout-sessions", help="Whether or not breakout sessions are enabled."),
    enabled_audio_watermark: bool = typer.Option(None, "--enabled-audio-watermark/--no-enabled-audio-watermark", help="Whether or not the audio watermark is enabled. If it's `true"),
    enabled_visual_watermark: bool = typer.Option(None, "--enabled-visual-watermark/--no-enabled-visual-watermark", help="Whether or not the visual watermark is enabled. If it's `tru"),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help="Opacity level for the visual watermark. The value must be be"),
    require_attendee_login: bool = typer.Option(None, "--require-attendee-login/--no-require-attendee-login", help="Require attendees to sign in before joining the webinar. Thi"),
    restrict_to_invitees: bool = typer.Option(None, "--restrict-to-invitees/--no-restrict-to-invitees", help="Restrict webinar to invited attendees only. This option work"),
    enabled_live_stream: bool = typer.Option(None, "--enabled-live-stream/--no-enabled-live-stream", help="Whether or not live streaming is enabled. If it's enabled, t"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Meeting\n\nExample --json-body:\n  '{"title":"...","start":"...","end":"...","adhoc":true,"roomId":"...","templateId":"...","agenda":"...","password":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if adhoc is not None:
            body["adhoc"] = adhoc
        if room_id is not None:
            body["roomId"] = room_id
        if template_id is not None:
            body["templateId"] = template_id
        if title is not None:
            body["title"] = title
        if agenda is not None:
            body["agenda"] = agenda
        if password is not None:
            body["password"] = password
        if start is not None:
            body["start"] = start
        if end is not None:
            body["end"] = end
        if timezone is not None:
            body["timezone"] = timezone
        if recurrence is not None:
            body["recurrence"] = recurrence
        if enabled_auto_record_meeting is not None:
            body["enabledAutoRecordMeeting"] = enabled_auto_record_meeting
        if allow_any_user_to_be_co_host is not None:
            body["allowAnyUserToBeCoHost"] = allow_any_user_to_be_co_host
        if enabled_join_before_host is not None:
            body["enabledJoinBeforeHost"] = enabled_join_before_host
        if enable_connect_audio_before_host is not None:
            body["enableConnectAudioBeforeHost"] = enable_connect_audio_before_host
        if join_before_host_minutes is not None:
            body["joinBeforeHostMinutes"] = join_before_host_minutes
        if exclude_password is not None:
            body["excludePassword"] = exclude_password
        if public_meeting is not None:
            body["publicMeeting"] = public_meeting
        if reminder_time is not None:
            body["reminderTime"] = reminder_time
        if unlocked_meeting_join_security is not None:
            body["unlockedMeetingJoinSecurity"] = unlocked_meeting_join_security
        if session_type_id is not None:
            body["sessionTypeId"] = session_type_id
        if scheduled_type is not None:
            body["scheduledType"] = scheduled_type
        if enabled_webcast_view is not None:
            body["enabledWebcastView"] = enabled_webcast_view
        if panelist_password is not None:
            body["panelistPassword"] = panelist_password
        if enable_automatic_lock is not None:
            body["enableAutomaticLock"] = enable_automatic_lock
        if automatic_lock_minutes is not None:
            body["automaticLockMinutes"] = automatic_lock_minutes
        if allow_first_user_to_be_co_host is not None:
            body["allowFirstUserToBeCoHost"] = allow_first_user_to_be_co_host
        if allow_authenticated_devices is not None:
            body["allowAuthenticatedDevices"] = allow_authenticated_devices
        if send_email is not None:
            body["sendEmail"] = send_email
        if host_email is not None:
            body["hostEmail"] = host_email
        if site_url is not None:
            body["siteUrl"] = site_url
        if enabled_breakout_sessions is not None:
            body["enabledBreakoutSessions"] = enabled_breakout_sessions
        if enabled_audio_watermark is not None:
            body["enabledAudioWatermark"] = enabled_audio_watermark
        if enabled_visual_watermark is not None:
            body["enabledVisualWatermark"] = enabled_visual_watermark
        if visual_watermark_opacity is not None:
            body["visualWatermarkOpacity"] = visual_watermark_opacity
        if require_attendee_login is not None:
            body["requireAttendeeLogin"] = require_attendee_login
        if restrict_to_invitees is not None:
            body["restrictToInvitees"] = restrict_to_invitees
        if enabled_live_stream is not None:
            body["enabledLiveStream"] = enabled_live_stream
        _missing = [f for f in ['title', 'start', 'end'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-meetings")
def show_meetings(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    meeting_id: str = typer.Argument(help="meetingId"),
    title: str = typer.Option(None, "--title", help="Meeting title. The title can be a maximum of 128 characters"),
    agenda: str = typer.Option(None, "--agenda", help="Meeting agenda. The agenda can be a maximum of 1300 characte"),
    password: str = typer.Option(None, "--password", help="Meeting password. Must conform to the site's password comple"),
    start: str = typer.Option(None, "--start", help="Date and time for the start of meeting in any [ISO 8601](htt"),
    end: str = typer.Option(None, "--end", help="Date and time for the end of meeting in any [ISO 8601](https"),
    timezone: str = typer.Option(None, "--timezone", help="[Time zone](https://en.wikipedia.org/wiki/List_of_tz_databas"),
    recurrence: str = typer.Option(None, "--recurrence", help="Meeting series recurrence rule (conforming with [RFC 2445](h"),
    enabled_auto_record_meeting: bool = typer.Option(None, "--enabled-auto-record-meeting/--no-enabled-auto-record-meeting", help="Whether or not meeting is recorded automatically."),
    allow_any_user_to_be_co_host: bool = typer.Option(None, "--allow-any-user-to-be-co-host/--no-allow-any-user-to-be-co-host", help="Whether or not to allow any attendee with a host account on"),
    enabled_join_before_host: bool = typer.Option(None, "--enabled-join-before-host/--no-enabled-join-before-host", help="Whether or not to allow any attendee to join the meeting bef"),
    enable_connect_audio_before_host: bool = typer.Option(None, "--enable-connect-audio-before-host/--no-enable-connect-audio-before-host", help="Whether or not to allow any attendee to connect audio in the"),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help="Number of minutes an attendee can join the meeting before th"),
    exclude_password: bool = typer.Option(None, "--exclude-password/--no-exclude-password", help="Whether or not to exclude the meeting password from the emai"),
    public_meeting: bool = typer.Option(None, "--public-meeting/--no-public-meeting", help="Whether or not to allow the meeting to be listed on the publ"),
    reminder_time: str = typer.Option(None, "--reminder-time", help="The number of minutes before the meeting begins, that an ema"),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help="Choices: allowJoin, allowJoinWithLobby, blockFromJoin"),
    session_type_id: str = typer.Option(None, "--session-type-id", help="Unique identifier for a meeting session type for the user. T"),
    enabled_webcast_view: bool = typer.Option(None, "--enabled-webcast-view/--no-enabled-webcast-view", help="Whether or not webcast view is enabled."),
    panelist_password: str = typer.Option(None, "--panelist-password", help="Password for panelists of a webinar meeting. Must conform to"),
    enable_automatic_lock: bool = typer.Option(None, "--enable-automatic-lock/--no-enable-automatic-lock", help="Whether or not to automatically lock the meeting after it st"),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help="The number of minutes after the meeting begins, for automati"),
    allow_first_user_to_be_co_host: bool = typer.Option(None, "--allow-first-user-to-be-co-host/--no-allow-first-user-to-be-co-host", help="Whether or not to allow the first attendee of the meeting wi"),
    allow_authenticated_devices: bool = typer.Option(None, "--allow-authenticated-devices/--no-allow-authenticated-devices", help="Whether or not to allow authenticated video devices in the m"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether or not to send emails to host and invitees. It is an"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    enabled_breakout_sessions: bool = typer.Option(None, "--enabled-breakout-sessions/--no-enabled-breakout-sessions", help="Whether or not breakout sessions are enabled. If the value o"),
    enabled_audio_watermark: bool = typer.Option(None, "--enabled-audio-watermark/--no-enabled-audio-watermark", help="Whether or not the audio watermark is enabled. If it's `true"),
    enabled_visual_watermark: bool = typer.Option(None, "--enabled-visual-watermark/--no-enabled-visual-watermark", help="Whether or not the visual watermark is enabled. If it's `tru"),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help="Opacity level for the visual watermark. The value must be be"),
    require_attendee_login: bool = typer.Option(None, "--require-attendee-login/--no-require-attendee-login", help="Require attendees to sign in before joining the webinar. Thi"),
    restrict_to_invitees: bool = typer.Option(None, "--restrict-to-invitees/--no-restrict-to-invitees", help="Restrict webinar to invited attendees only. This option work"),
    enabled_live_stream: bool = typer.Option(None, "--enabled-live-stream/--no-enabled-live-stream", help="Whether or not live streaming is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Meeting\n\nExample --json-body:\n  '{"title":"...","agenda":"...","password":"...","start":"...","end":"...","timezone":"...","recurrence":"...","enabledAutoRecordMeeting":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if title is not None:
            body["title"] = title
        if agenda is not None:
            body["agenda"] = agenda
        if password is not None:
            body["password"] = password
        if start is not None:
            body["start"] = start
        if end is not None:
            body["end"] = end
        if timezone is not None:
            body["timezone"] = timezone
        if recurrence is not None:
            body["recurrence"] = recurrence
        if enabled_auto_record_meeting is not None:
            body["enabledAutoRecordMeeting"] = enabled_auto_record_meeting
        if allow_any_user_to_be_co_host is not None:
            body["allowAnyUserToBeCoHost"] = allow_any_user_to_be_co_host
        if enabled_join_before_host is not None:
            body["enabledJoinBeforeHost"] = enabled_join_before_host
        if enable_connect_audio_before_host is not None:
            body["enableConnectAudioBeforeHost"] = enable_connect_audio_before_host
        if join_before_host_minutes is not None:
            body["joinBeforeHostMinutes"] = join_before_host_minutes
        if exclude_password is not None:
            body["excludePassword"] = exclude_password
        if public_meeting is not None:
            body["publicMeeting"] = public_meeting
        if reminder_time is not None:
            body["reminderTime"] = reminder_time
        if unlocked_meeting_join_security is not None:
            body["unlockedMeetingJoinSecurity"] = unlocked_meeting_join_security
        if session_type_id is not None:
            body["sessionTypeId"] = session_type_id
        if enabled_webcast_view is not None:
            body["enabledWebcastView"] = enabled_webcast_view
        if panelist_password is not None:
            body["panelistPassword"] = panelist_password
        if enable_automatic_lock is not None:
            body["enableAutomaticLock"] = enable_automatic_lock
        if automatic_lock_minutes is not None:
            body["automaticLockMinutes"] = automatic_lock_minutes
        if allow_first_user_to_be_co_host is not None:
            body["allowFirstUserToBeCoHost"] = allow_first_user_to_be_co_host
        if allow_authenticated_devices is not None:
            body["allowAuthenticatedDevices"] = allow_authenticated_devices
        if send_email is not None:
            body["sendEmail"] = send_email
        if host_email is not None:
            body["hostEmail"] = host_email
        if enabled_breakout_sessions is not None:
            body["enabledBreakoutSessions"] = enabled_breakout_sessions
        if enabled_audio_watermark is not None:
            body["enabledAudioWatermark"] = enabled_audio_watermark
        if enabled_visual_watermark is not None:
            body["enabledVisualWatermark"] = enabled_visual_watermark
        if visual_watermark_opacity is not None:
            body["visualWatermarkOpacity"] = visual_watermark_opacity
        if require_attendee_login is not None:
            body["requireAttendeeLogin"] = require_attendee_login
        if restrict_to_invitees is not None:
            body["restrictToInvitees"] = restrict_to_invitees
        if enabled_live_stream is not None:
            body["enabledLiveStream"] = enabled_live_stream
    try:
        result = api.session.rest_put(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("update-meetings")
def update_meetings(
    meeting_id: str = typer.Argument(help="meetingId"),
    title: str = typer.Option(None, "--title", help="Meeting title. The title can be a maximum of 128 characters"),
    agenda: str = typer.Option(None, "--agenda", help="Meeting agenda. The agenda can be a maximum of 1300 characte"),
    password: str = typer.Option(None, "--password", help="Meeting password. Must conform to the site's password comple"),
    start: str = typer.Option(None, "--start", help="Date and time for the start of meeting in any [ISO 8601](htt"),
    end: str = typer.Option(None, "--end", help="Date and time for the end of meeting in any [ISO 8601](https"),
    timezone: str = typer.Option(None, "--timezone", help="[Time zone](https://en.wikipedia.org/wiki/List_of_tz_databas"),
    recurrence: str = typer.Option(None, "--recurrence", help="Meeting series recurrence rule (conforming with [RFC 2445](h"),
    enabled_auto_record_meeting: str = typer.Option(None, "--enabled-auto-record-meeting", help="Whether or not meeting is recorded automatically."),
    allow_any_user_to_be_co_host: str = typer.Option(None, "--allow-any-user-to-be-co-host", help="Whether or not to allow any attendee with a host account on"),
    enabled_join_before_host: str = typer.Option(None, "--enabled-join-before-host", help="Whether or not to allow any attendee to join the meeting bef"),
    enable_connect_audio_before_host: str = typer.Option(None, "--enable-connect-audio-before-host", help="Whether or not to allow any attendee to connect audio in the"),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help="Number of minutes an attendee can join the meeting before th"),
    exclude_password: str = typer.Option(None, "--exclude-password", help="Whether or not to exclude the meeting password from the emai"),
    public_meeting: str = typer.Option(None, "--public-meeting", help="Whether or not to allow the meeting to be listed on the publ"),
    reminder_time: str = typer.Option(None, "--reminder-time", help="The number of minutes before the meeting begins, that an ema"),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help="Choices: allowJoin, allowJoinWithLobby, blockFromJoin"),
    session_type_id: str = typer.Option(None, "--session-type-id", help="Unique identifier for a meeting session type for the user. T"),
    enabled_webcast_view: str = typer.Option(None, "--enabled-webcast-view", help="Whether or not webcast view is enabled."),
    panelist_password: str = typer.Option(None, "--panelist-password", help="Password for panelists of a webinar meeting. Must conform to"),
    enable_automatic_lock: str = typer.Option(None, "--enable-automatic-lock", help="Whether or not to automatically lock the meeting after it st"),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help="The number of minutes after the meeting begins, for automati"),
    allow_first_user_to_be_co_host: str = typer.Option(None, "--allow-first-user-to-be-co-host", help="Whether or not to allow the first attendee of the meeting wi"),
    allow_authenticated_devices: str = typer.Option(None, "--allow-authenticated-devices", help="Whether or not to allow authenticated video devices in the m"),
    send_email: str = typer.Option(None, "--send-email", help="Whether or not to send emails to host and invitees. It is an"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    enabled_breakout_sessions: str = typer.Option(None, "--enabled-breakout-sessions", help="Whether or not breakout sessions are enabled. If the value o"),
    enabled_audio_watermark: str = typer.Option(None, "--enabled-audio-watermark", help="Whether or not the audio watermark is enabled. If it's `true"),
    enabled_visual_watermark: str = typer.Option(None, "--enabled-visual-watermark", help="Whether or not the visual watermark is enabled. If it's `tru"),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help="Opacity level for the visual watermark. The value must be be"),
    require_attendee_login: str = typer.Option(None, "--require-attendee-login", help="Require attendees to sign in before joining the webinar. Thi"),
    restrict_to_invitees: str = typer.Option(None, "--restrict-to-invitees", help="Restrict webinar to invited attendees only. This option work"),
    enabled_live_stream: str = typer.Option(None, "--enabled-live-stream", help="Whether or not live streaming is enabled."),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Patch a Meeting\n\nExample --json-body:\n  '{"title":"...","agenda":"...","password":"...","start":"...","end":"...","timezone":"...","recurrence":"...","enabledAutoRecordMeeting":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        patch_op = {}
        if title is not None:
            patch_op["title"] = title
        if agenda is not None:
            patch_op["agenda"] = agenda
        if password is not None:
            patch_op["password"] = password
        if start is not None:
            patch_op["start"] = start
        if end is not None:
            patch_op["end"] = end
        if timezone is not None:
            patch_op["timezone"] = timezone
        if recurrence is not None:
            patch_op["recurrence"] = recurrence
        if enabled_auto_record_meeting is not None:
            patch_op["enabledAutoRecordMeeting"] = enabled_auto_record_meeting
        if allow_any_user_to_be_co_host is not None:
            patch_op["allowAnyUserToBeCoHost"] = allow_any_user_to_be_co_host
        if enabled_join_before_host is not None:
            patch_op["enabledJoinBeforeHost"] = enabled_join_before_host
        if enable_connect_audio_before_host is not None:
            patch_op["enableConnectAudioBeforeHost"] = enable_connect_audio_before_host
        if join_before_host_minutes is not None:
            patch_op["joinBeforeHostMinutes"] = join_before_host_minutes
        if exclude_password is not None:
            patch_op["excludePassword"] = exclude_password
        if public_meeting is not None:
            patch_op["publicMeeting"] = public_meeting
        if reminder_time is not None:
            patch_op["reminderTime"] = reminder_time
        if unlocked_meeting_join_security is not None:
            patch_op["unlockedMeetingJoinSecurity"] = unlocked_meeting_join_security
        if session_type_id is not None:
            patch_op["sessionTypeId"] = session_type_id
        if enabled_webcast_view is not None:
            patch_op["enabledWebcastView"] = enabled_webcast_view
        if panelist_password is not None:
            patch_op["panelistPassword"] = panelist_password
        if enable_automatic_lock is not None:
            patch_op["enableAutomaticLock"] = enable_automatic_lock
        if automatic_lock_minutes is not None:
            patch_op["automaticLockMinutes"] = automatic_lock_minutes
        if allow_first_user_to_be_co_host is not None:
            patch_op["allowFirstUserToBeCoHost"] = allow_first_user_to_be_co_host
        if allow_authenticated_devices is not None:
            patch_op["allowAuthenticatedDevices"] = allow_authenticated_devices
        if send_email is not None:
            patch_op["sendEmail"] = send_email
        if host_email is not None:
            patch_op["hostEmail"] = host_email
        if enabled_breakout_sessions is not None:
            patch_op["enabledBreakoutSessions"] = enabled_breakout_sessions
        if enabled_audio_watermark is not None:
            patch_op["enabledAudioWatermark"] = enabled_audio_watermark
        if enabled_visual_watermark is not None:
            patch_op["enabledVisualWatermark"] = enabled_visual_watermark
        if visual_watermark_opacity is not None:
            patch_op["visualWatermarkOpacity"] = visual_watermark_opacity
        if require_attendee_login is not None:
            patch_op["requireAttendeeLogin"] = require_attendee_login
        if restrict_to_invitees is not None:
            patch_op["restrictToInvitees"] = restrict_to_invitees
        if enabled_live_stream is not None:
            patch_op["enabledLiveStream"] = enabled_live_stream
        if value is not None:
            try:
                patch_op["value"] = json.loads(value)
            except json.JSONDecodeError:
                patch_op["value"] = value
        body = [patch_op]
    try:
        result = api.session.rest_patch(url, json=body, content_type="application/json-patch+json")
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help="Whether or not to send emails to host and invitees. It is an"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting."""
    if not force:
        typer.confirm(f"Delete {meeting_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if send_email is not None:
        params["sendEmail"] = send_email
    try:
        api.session.rest_delete(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {meeting_id}")



@app.command("create-join")
def create_join(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the meeting. This parameter applies to"),
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number. Applies to meeting series, scheduled meeting"),
    web_link: str = typer.Option(None, "--web-link", help="Link to a meeting information page where the meeting client"),
    join_directly: bool = typer.Option(None, "--join-directly/--no-join-directly", help="Whether or not to redirect to `joinLink`. It is an optional"),
    email: str = typer.Option(None, "--email", help="Email address of meeting participant. If `email` is specifie"),
    display_name: str = typer.Option(None, "--display-name", help="Display name of meeting participant. If `displayName` is spe"),
    password: str = typer.Option(None, "--password", help="Required when the meeting is protected by a password and the"),
    expiration_minutes: str = typer.Option(None, "--expiration-minutes", help="Expiration duration of `joinLink` in minutes. Must be betwee"),
    registration_id: str = typer.Option(None, "--registration-id", help="Required when the meeting is webinar-enabled and enabled reg"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should be"),
    create_join_link_as_web_link: bool = typer.Option(None, "--create-join-link-as-web-link/--no-create-join-link-as-web-link", help="When `createJoinLinkAsWebLink` is true, the returned `joinLi"),
    create_start_link_as_web_link: bool = typer.Option(None, "--create-start-link-as-web-link/--no-create-start-link-as-web-link", help="When `createStartLinkAsWebLink` is true, the returned `start"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Join a Meeting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/join"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if meeting_id is not None:
            body["meetingId"] = meeting_id
        if meeting_number is not None:
            body["meetingNumber"] = meeting_number
        if web_link is not None:
            body["webLink"] = web_link
        if join_directly is not None:
            body["joinDirectly"] = join_directly
        if email is not None:
            body["email"] = email
        if display_name is not None:
            body["displayName"] = display_name
        if password is not None:
            body["password"] = password
        if expiration_minutes is not None:
            body["expirationMinutes"] = expiration_minutes
        if registration_id is not None:
            body["registrationId"] = registration_id
        if host_email is not None:
            body["hostEmail"] = host_email
        if create_join_link_as_web_link is not None:
            body["createJoinLinkAsWebLink"] = create_join_link_as_web_link
        if create_start_link_as_web_link is not None:
            body["createStartLinkAsWebLink"] = create_start_link_as_web_link
    try:
        result = api.session.rest_post(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-templates")
def list_templates(
    template_type: str = typer.Option(None, "--template-type", help="Choices: meeting, webinar"),
    locale: str = typer.Option(None, "--locale", help="Locale for the meeting template objects being requested. If"),
    is_default: str = typer.Option(None, "--is-default", help="The value is `true` or `false`. If it's `true`, return the d"),
    is_standard: str = typer.Option(None, "--is-standard", help="The value is `true` or `false`. If it's `true`, return the s"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meeting templates"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Templates."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/templates"
    params = {}
    if template_type is not None:
        params["templateType"] = template_type
    if locale is not None:
        params["locale"] = locale
    if is_default is not None:
        params["isDefault"] = is_default
    if is_standard is not None:
        params["isStandard"] = is_standard
    if host_email is not None:
        params["hostEmail"] = host_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("show-templates")
def show_templates(
    template_id: str = typer.Argument(help="templateId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Template."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/templates/{template_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("show-controls")
def show_controls(
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the meeting. Does not support meeting"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Control Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/controls"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-controls")
def update_controls(
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the meeting. Does not support meeting"),
    recording_started: bool = typer.Option(None, "--recording-started/--no-recording-started", help="The value can be true or false. true means to start the reco"),
    recording_paused: bool = typer.Option(None, "--recording-paused/--no-recording-paused", help="The value can be true or false, will be ignored if 'recordin"),
    locked: bool = typer.Option(None, "--locked/--no-locked", help="The value is true or false."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Control Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/controls"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if recording_started is not None:
            body["recordingStarted"] = recording_started
        if recording_paused is not None:
            body["recordingPaused"] = recording_paused
        if locked is not None:
            body["locked"] = locked
    try:
        result = api.session.rest_put(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-session-types")
def list_session_types(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="Webex site URL to query. If `siteUrl` is not specified, the"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Session Types."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/sessionTypes"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("show-session-types")
def show_session_types(
    session_type_id: str = typer.Argument(help="sessionTypeId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="Webex site URL to query. If `siteUrl` is not specified, the"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Session Type."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/sessionTypes/{session_type_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if site_url is not None:
        params["siteUrl"] = site_url
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("list-registration")
def list_registration(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get registration form for a meeting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registration"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("customizedQuestions", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("update-registration")
def update_registration(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="- Email address for the meeting host. This parameter is only"),
    auto_accept_request: bool = typer.Option(None, "--auto-accept-request/--no-auto-accept-request", help="Whether or not meeting registration requests are accepted au"),
    require_first_name: bool = typer.Option(None, "--require-first-name/--no-require-first-name", help="Whether or not a registrant's first name is required for mee"),
    require_last_name: bool = typer.Option(None, "--require-last-name/--no-require-last-name", help="Whether or not a registrant's last name is required for meet"),
    require_email: bool = typer.Option(None, "--require-email/--no-require-email", help="Whether or not a registrant's email is required for meeting"),
    require_job_title: bool = typer.Option(None, "--require-job-title/--no-require-job-title", help="Whether or not a registrant's job title is shown or required"),
    require_company_name: bool = typer.Option(None, "--require-company-name/--no-require-company-name", help="Whether or not a registrant's company name is shown or requi"),
    require_address1: bool = typer.Option(None, "--require-address1/--no-require-address1", help="Whether or not a registrant's first address field is shown o"),
    require_address2: bool = typer.Option(None, "--require-address2/--no-require-address2", help="Whether or not a registrant's second address field is shown"),
    require_city: bool = typer.Option(None, "--require-city/--no-require-city", help="Whether or not a registrant's city is shown or required for"),
    require_state: bool = typer.Option(None, "--require-state/--no-require-state", help="Whether or not a registrant's state is shown or required for"),
    require_zip_code: bool = typer.Option(None, "--require-zip-code/--no-require-zip-code", help="Whether or not a registrant's postal code is shown or requir"),
    require_country_region: bool = typer.Option(None, "--require-country-region/--no-require-country-region", help="Whether or not a registrant's country or region is shown or"),
    require_work_phone: bool = typer.Option(None, "--require-work-phone/--no-require-work-phone", help="Whether or not a registrant's work phone number is shown or"),
    require_fax: bool = typer.Option(None, "--require-fax/--no-require-fax", help="Whether or not a registrant's fax number is shown or require"),
    max_register_num: str = typer.Option(None, "--max-register-num", help="Maximum number of meeting registrations. This only applies t"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Registration Form\n\nExample --json-body:\n  '{"hostEmail":"...","autoAcceptRequest":true,"requireFirstName":true,"requireLastName":true,"requireEmail":true,"requireJobTitle":true,"requireCompanyName":true,"requireAddress1":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registration"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if auto_accept_request is not None:
            body["autoAcceptRequest"] = auto_accept_request
        if require_first_name is not None:
            body["requireFirstName"] = require_first_name
        if require_last_name is not None:
            body["requireLastName"] = require_last_name
        if require_email is not None:
            body["requireEmail"] = require_email
        if require_job_title is not None:
            body["requireJobTitle"] = require_job_title
        if require_company_name is not None:
            body["requireCompanyName"] = require_company_name
        if require_address1 is not None:
            body["requireAddress1"] = require_address1
        if require_address2 is not None:
            body["requireAddress2"] = require_address2
        if require_city is not None:
            body["requireCity"] = require_city
        if require_state is not None:
            body["requireState"] = require_state
        if require_zip_code is not None:
            body["requireZipCode"] = require_zip_code
        if require_country_region is not None:
            body["requireCountryRegion"] = require_country_region
        if require_work_phone is not None:
            body["requireWorkPhone"] = require_work_phone
        if require_fax is not None:
            body["requireFax"] = require_fax
        if max_register_num is not None:
            body["maxRegisterNum"] = max_register_num
    try:
        result = api.session.rest_put(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-registration")
def delete_registration(
    meeting_id: str = typer.Argument(help="meetingId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Meeting Registration Form."""
    if not force:
        typer.confirm(f"Delete {meeting_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registration"
    try:
        api.session.rest_delete(url)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {meeting_id}")



@app.command("list-registrants")
def list_registrants(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    email: str = typer.Option(None, "--email", help="Registrant's email to filter registrants."),
    registration_time_from: str = typer.Option(None, "--registration-time-from", help="The time registrants register a meeting starts from the spec"),
    registration_time_to: str = typer.Option(None, "--registration-time-to", help="The time registrants register a meeting before the specified"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Registrants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if current is not None:
        params["current"] = current
    if email is not None:
        params["email"] = email
    if registration_time_from is not None:
        params["registrationTimeFrom"] = registration_time_from
    if registration_time_to is not None:
        params["registrationTimeTo"] = registration_time_to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-registrants")
def create_registrants(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    first_name: str = typer.Option(None, "--first-name", help="(required) The registrant's first name."),
    last_name: str = typer.Option(None, "--last-name", help="(required) The registrant's last name. (Required)"),
    email: str = typer.Option(None, "--email", help="(required) The registrant's email."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to the registrant. Default: `true`."),
    job_title: str = typer.Option(None, "--job-title", help="The registrant's job title. Registration options define whet"),
    company_name: str = typer.Option(None, "--company-name", help="The registrant's company. Registration options define whethe"),
    address1: str = typer.Option(None, "--address1", help="The registrant's first address line. Registration options de"),
    address2: str = typer.Option(None, "--address2", help="The registrant's second address line. Registration options d"),
    city: str = typer.Option(None, "--city", help="The registrant's city name. Registration options define whet"),
    state: str = typer.Option(None, "--state", help="The registrant's state. Registration options define whether"),
    zip_code: str = typer.Option(None, "--zip-code", help="The registrant's postal code. Registration options define wh"),
    country_region: str = typer.Option(None, "--country-region", help="The America is not a country or a specific region. Registrat"),
    work_phone: str = typer.Option(None, "--work-phone", help="The registrant's work phone number. Registration options def"),
    fax: str = typer.Option(None, "--fax", help="The registrant's FAX number. Registration options define whe"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Register a Meeting Registrant\n\nExample --json-body:\n  '{"firstName":"...","lastName":"...","email":"...","sendEmail":true,"jobTitle":"...","companyName":"...","address1":"...","address2":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if email is not None:
            body["email"] = email
        if send_email is not None:
            body["sendEmail"] = send_email
        if job_title is not None:
            body["jobTitle"] = job_title
        if company_name is not None:
            body["companyName"] = company_name
        if address1 is not None:
            body["address1"] = address1
        if address2 is not None:
            body["address2"] = address2
        if city is not None:
            body["city"] = city
        if state is not None:
            body["state"] = state
        if zip_code is not None:
            body["zipCode"] = zip_code
        if country_region is not None:
            body["countryRegion"] = country_region
        if work_phone is not None:
            body["workPhone"] = work_phone
        if fax is not None:
            body["fax"] = fax
        _missing = [f for f in ['firstName', 'lastName', 'email'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch register Meeting Registrants\n\nExample --json-body:\n  '{"items":[{"firstName":"...","lastName":"...","email":"...","sendEmail":"...","jobTitle":"...","companyName":"...","address1":"...","address2":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/bulkInsert"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-registrants")
def show_registrants(
    meeting_id: str = typer.Argument(help="meetingId"),
    registrant_id: str = typer.Argument(help="registrantId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Detailed Information for a Meeting Registrant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/{registrant_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("delete-registrants")
def delete_registrants(
    meeting_id: str = typer.Argument(help="meetingId"),
    registrant_id: str = typer.Argument(help="registrantId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Registrant."""
    if not force:
        typer.confirm(f"Delete {registrant_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/{registrant_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        api.session.rest_delete(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {registrant_id}")



@app.command("create-query")
def create_query(
    meeting_id: str = typer.Argument(help="meetingId"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of registrants in the response, up"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    status: str = typer.Option(None, "--status", help="Choices: approved, pending, rejected"),
    order_type: str = typer.Option(None, "--order-type", help="Choices: DESC, ASC"),
    order_by: str = typer.Option(None, "--order-by", help="Choices: firstName, lastName, status, email"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Meeting Registrants\n\nExample --json-body:\n  '{"emails":["..."],"status":"approved","orderType":"DESC","orderBy":"firstName"}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/query"
    params = {}
    if max is not None:
        params["max"] = max
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if status is not None:
            body["status"] = status
        if order_type is not None:
            body["orderType"] = order_type
        if order_by is not None:
            body["orderBy"] = order_by
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-approve")
def create_approve(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to registrants. Default: `true`."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Approve Meeting Registrants\n\nExample --json-body:\n  '{"sendEmail":true,"registrants":[{"id":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/approve"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-reject")
def create_reject(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to registrants. Default: `true`."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Reject Meeting Registrants\n\nExample --json-body:\n  '{"sendEmail":true,"registrants":[{"id":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/reject"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-cancel")
def create_cancel(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to registrants. Default: `true`."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Cancel Meeting Registrants\n\nExample --json-body:\n  '{"sendEmail":true,"registrants":[{"id":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/cancel"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-bulk-delete")
def create_bulk_delete(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to registrants. Default: `true`."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Delete Meeting Registrants\n\nExample --json-body:\n  '{"sendEmail":true,"registrants":[{"id":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/bulkDelete"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("update-simultaneous-interpretation")
def update_simultaneous_interpretation(
    meeting_id: str = typer.Argument(help="meetingId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not simultaneous interpretation is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Simultaneous interpretation\n\nExample --json-body:\n  '{"enabled":true,"interpreters":[{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/simultaneousInterpretation"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-interpreters")
def list_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Interpreters."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-interpreters")
def create_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    language_code1: str = typer.Option(None, "--language-code1", help="(required) The pair of `languageCode1` and `languageCode2` form a bi-di"),
    language_code2: str = typer.Option(None, "--language-code2", help="(required) The pair of `languageCode1` and `languageCode2` form a bi-di"),
    email: str = typer.Option(None, "--email", help="Email address of meeting interpreter. If not specified, an e"),
    display_name: str = typer.Option(None, "--display-name", help="Display name of meeting interpreter. If the interpreter is a"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true`, send email to the interpreter."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Meeting Interpreter."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if language_code1 is not None:
            body["languageCode1"] = language_code1
        if language_code2 is not None:
            body["languageCode2"] = language_code2
        if email is not None:
            body["email"] = email
        if display_name is not None:
            body["displayName"] = display_name
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
        _missing = [f for f in ['languageCode1', 'languageCode2'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-interpreters")
def show_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    interpreter_id: str = typer.Argument(help="interpreterId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Interpreter."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-interpreters")
def update_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    interpreter_id: str = typer.Argument(help="interpreterId"),
    language_code1: str = typer.Option(None, "--language-code1", help="The pair of `languageCode1` and `languageCode2` form a bi-di"),
    language_code2: str = typer.Option(None, "--language-code2", help="The pair of `languageCode1` and `languageCode2` form a bi-di"),
    email: str = typer.Option(None, "--email", help="Email address of meeting interpreter. If not specified, it'l"),
    display_name: str = typer.Option(None, "--display-name", help="Display name of meeting interpreter. If the interpreter is a"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true`, send email to the interpreter."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Meeting Interpreter."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if language_code1 is not None:
            body["languageCode1"] = language_code1
        if language_code2 is not None:
            body["languageCode2"] = language_code2
        if email is not None:
            body["email"] = email
        if display_name is not None:
            body["displayName"] = display_name
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_put(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-interpreters")
def delete_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    interpreter_id: str = typer.Argument(help="interpreterId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help="If `true`, send email to the interpreter."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Interpreter."""
    if not force:
        typer.confirm(f"Delete {interpreter_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if send_email is not None:
        params["sendEmail"] = send_email
    try:
        api.session.rest_delete(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {interpreter_id}")



@app.command("list-breakout-sessions")
def list_breakout_sessions(
    meeting_id: str = typer.Argument(help="meetingId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Breakout Sessions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("update-breakout-sessions")
def update_breakout_sessions(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether or not to send emails to host and invitees. It is an"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Breakout Sessions\n\nExample --json-body:\n  '{"hostEmail":"...","sendEmail":true,"items":[{"name":"...","invitees":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_put(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-breakout-sessions")
def delete_breakout_sessions(
    meeting_id: str = typer.Argument(help="meetingId"),
    send_email: str = typer.Option(None, "--send-email", help="Whether or not to send emails to host and invitees. It is an"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Meeting Breakout Sessions."""
    if not force:
        typer.confirm(f"Delete {meeting_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    params = {}
    if send_email is not None:
        params["sendEmail"] = send_email
    try:
        api.session.rest_delete(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {meeting_id}")



@app.command("list-survey")
def list_survey(
    meeting_id: str = typer.Argument(help="meetingId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Survey."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/survey"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("questions", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("list-survey-results")
def list_survey_results(
    meeting_id: str = typer.Argument(help="meetingId"),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Start date and time (inclusive) in any [ISO 8601](https://en"),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="End date and time (exclusive) in any [ISO 8601](https://en.w"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Survey Results."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/surveyResults"
    params = {}
    if meeting_start_time_from is not None:
        params["meetingStartTimeFrom"] = meeting_start_time_from
    if meeting_start_time_to is not None:
        params["meetingStartTimeTo"] = meeting_start_time_to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-survey-links")
def create_survey_links(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Start date and time (inclusive) in any [ISO 8601](https://en"),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="End date and time (exclusive) in any [ISO 8601](https://en.w"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Survey Links\n\nExample --json-body:\n  '{"hostEmail":"...","meetingStartTimeFrom":"...","meetingStartTimeTo":"...","emails":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/surveyLinks"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if meeting_start_time_from is not None:
            body["meetingStartTimeFrom"] = meeting_start_time_from
        if meeting_start_time_to is not None:
            body["meetingStartTimeTo"] = meeting_start_time_to
    try:
        result = api.session.rest_post(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-invitation-sources")
def list_invitation_sources(
    meeting_id: str = typer.Argument(help="meetingId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Invitation Sources."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/invitationSources"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-invitation-sources")
def create_invitation_sources(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    person_id: str = typer.Option(None, "--person-id", help="Unique identifier for the meeting host. Should only be set i"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Invitation Sources\n\nExample --json-body:\n  '{"hostEmail":"...","personId":"...","items":[{"sourceId":"...","sourceEmail":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/invitationSources"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if person_id is not None:
            body["personId"] = person_id
    try:
        result = api.session.rest_post(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-tracking-codes")
def list_tracking_codes(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API retrieves the tracking c"),
    service: str = typer.Option(..., "--service", help="Service for schedule or sign-up pages."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Tracking Codes."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/trackingCodes"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    if service is not None:
        params["service"] = service
    if host_email is not None:
        params["hostEmail"] = host_email
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-reassign-host")
def create_reassign_host(
    host_email: str = typer.Option(None, "--host-email", help="(required) Email address of the new meeting host."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reassign Meetings to a New Host\n\nExample --json-body:\n  '{"hostEmail":"...","meetingIds":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/reassignHost"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        _missing = [f for f in ['hostEmail'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-end")
def create_end(
    meeting_id: str = typer.Argument(help="meetingId"),
    reason: str = typer.Option(None, "--reason", help="The reason for ending the meeting. This field is optional."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """End a Meeting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/end"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if reason is not None:
            body["reason"] = reason
    try:
        result = api.session.rest_post(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


