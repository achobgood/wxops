import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meetings.")


@app.command("show", short_help="Get a Meeting By an Admin.")
def show(
    meeting_id: str = typer.Argument(help="UUID, from: wxcli meetings list"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting By an Admin.\n\n\b\nExample: wxcli meetings show MEETING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetings/{meeting_id}"
    params = {}
    if current is not None:
        params["current"] = current
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list", short_help="List Meetings By an Admin.")
def cmd_list(
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number for the meeting objects being requested. `meetingNumber` and `webLink` are mutually exclusive. If it's an exceptional meeting from a meeting series, the exceptional meeting instead of the primary meeting series is returned."),
    web_link: str = typer.Option(None, "--web-link", help="URL encoded link to information page for the meeting objects being requested. `meetingNumber` and `webLink` are mutually exclusive."),
    current: str = typer.Option(None, "--current", help="Flag identifying to retrieve the current scheduled meeting of the meeting series or the entire meeting series. This parameter only applies to scenarios where `meetingNumber` is specified and the meeting is not an exceptional meeting from a meeting series. If it's `true`, return the scheduled..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            if "max" not in params:
                params["max"] = 1000
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("list-meetings", short_help="List Meetings.")
def list_meetings(
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number for the meeting objects being requested. `meetingNumber`, `webLink` and `roomId` are mutually exclusive. If it's an exceptional meeting from a meeting series, the exceptional meeting instead of the primary meeting series is returned."),
    web_link: str = typer.Option(None, "--web-link", help="URL encoded link to information page for the meeting objects being requested. `meetingNumber`, `webLink` and `roomId` are mutually exclusive."),
    room_id: str = typer.Option(None, "--room-id", help="Associated Webex space ID for the meeting objects being requested. `meetingNumber`, `webLink` and `roomId` are mutually exclusive."),
    meeting_series_id: str = typer.Option(None, "--meeting-series-id", help="Unique identifier for the meeting series. The meeting ID of a scheduled [personal room](https://help.webex.com/en-us/article/nul0wut/Webex-Personal-Rooms-in-Webex-Meetings) meeting is not supported. If `meetingSeriesId` is specified, it lists all occurrences and instances of the meeting series by..."),
    from_param: str = typer.Option(None, "--from", help="Start date and time (inclusive) for the range for which meetings are to be returned in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. This parameter will be ignored if `meetingNumber`, `webLink` or `roomId` is specified. When `meetingType` is..."),
    to: str = typer.Option(None, "--to", help="End date and time (exclusive) for the range for which meetings are to be returned in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. This parameter will be ignored if `meetingNumber`, `webLink` or `roomId` is specified. When `meetingType` is..."),
    meeting_type: str = typer.Option(None, "--meeting-type", help="Choices: meetingSeries, scheduledMeeting, meeting"),
    state: str = typer.Option(None, "--state", help="Choices: active, scheduled, ready, lobby, inProgress, ended, missed, expired"),
    scheduled_type: str = typer.Option(None, "--scheduled-type", help="Choices: meeting, webinar, personalRoomMeeting"),
    is_modified: str = typer.Option(None, "--is-modified", help="Flag identifying whether a meeting has been modified. Only applies to scheduled meetings. If `true`, only return modified scheduled meetings; if `false`, only return unmodified scheduled meetings; if not specified, all scheduled meetings will be returned."),
    has_chat: str = typer.Option(None, "--has-chat", help="Flag identifying whether a meeting has a chat log. Only applies to ended meeting instances. If `true`, only return meeting instances which have chats; if `false`, only return meeting instances which have no chats; if not specified, all meeting instances will be returned."),
    has_recording: str = typer.Option(None, "--has-recording", help="Flag identifying meetings which have been recorded. Only applies to ended meeting instances. If true, only return meeting instances which have been recorded; if false, only return meeting instances which have not been recorded; if not specified, all meeting instances will be returned."),
    has_transcription: str = typer.Option(None, "--has-transcription", help="Flag identifying meetings with transcripts. Only applies to ended meeting instances. If `true`, only return meeting instances which have transcripts; if `false`, only return meeting instances which have no transcripts; if not specified, all meeting instances will be returned."),
    has_summary: str = typer.Option(None, "--has-summary", help="Flag identifying meetings with summaries. Only applies to ended meeting instances. If `true`, only return meeting instances which have summaries; if `false`, only return meeting instances which have no summaries; if not specified, all meeting instances will be returned."),
    has_closed_caption: str = typer.Option(None, "--has-closed-caption", help="Flag identifying meetings with closed captions. Only applies to ended meeting instances. If `true`, only return meeting instances which have closed captions; if `false`, only return meeting instances which have no closed captions; if not specified, all meeting instances will be returned."),
    has_polls: str = typer.Option(None, "--has-polls", help="Flag identifying meetings with polls. Only applies to ended meeting instances. If `true`, only return meeting instances which have polls; if `false`, only return meeting instances which have no polls; if not specified, all meeting instances will be returned."),
    has_qa: str = typer.Option(None, "--has-qa", help="Flag identifying meetings with Q&A. Only applies to ended meeting instances. If `true`, only return meeting instances which have Q&A; if `false`, only return meeting instances which have no Q&A; if not specified, all meeting instances will be returned."),
    has_slido: str = typer.Option(None, "--has-slido", help="Flag identifying meetings with Slido interactions. Only applies to ended meeting instances. If `true`, only return meeting instances which have Slido interactions like Q&A or polling; if `false`, only return meeting instances which have no Slido interactions; if not specified, all meeting instances..."),
    current: str = typer.Option(None, "--current", help="Flag identifying to retrieve the current scheduled meeting of the meeting series or the entire meeting series. This parameter only applies to scenarios where the meeting is not an exceptional meeting from a meeting series. If it's `true`, return the scheduled meeting of the meeting series which is..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API returns meetings as if the user calling the API were the user of `hostEmail`..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meetings from. If not specified, the API lists meetings from user's all sites. All available Webex sites of the user can be retrieved by `Get Site List` API."),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key created by an integration application. This parameter is used by the integration application to query meetings by a key in its own domain such as a Zendesk ticket ID, a Jira ID, a Salesforce Opportunity ID, etc. An integrationTag created by one client cannot be accessed or used as a..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Title', 'title'), ('Meeting Series ID', 'meetingSeriesId'), ('Scheduled Meeting ID', 'scheduledMeetingId'), ('Meeting Number', 'meetingNumber')], limit=limit)



_BODY_SKELETON_CREATE = '{"title":"...","start":"...","end":"...","adhoc":true,"roomId":"...","templateId":"...","agenda":"...","password":"...","timezone":"...","recurrence":"...","enabledAutoRecordMeeting":true,"allowAnyUserToBeCoHost":true,"enabledJoinBeforeHost":true,"enableConnectAudioBeforeHost":true,"joinBeforeHostMinutes":0,"excludePassword":true,"publicMeeting":true,"reminderTime":0,"unlockedMeetingJoinSecurity":"allowJoin","sessionTypeId":0,"scheduledType":"meeting","enabledWebcastView":true,"panelistPassword":"...","enableAutomaticLock":true,"automaticLockMinutes":0,"allowFirstUserToBeCoHost":true,"allowAuthenticatedDevices":true,"invitees":[{"email":"...","displayName":"...","coHost":true,"panelist":true}],"sendEmail":true,"hostEmail":"...","siteUrl":"...","meetingOptions":{"enabledChat":true,"enabledVideo":true,"enabledPolling":true,"enabledNote":true,"noteType":"allowAll","enabledFileTransfer":true,"enabledUCFRichMedia":true},"attendeePrivileges":{"enabledShareContent":true,"enabledSaveDocument":true,"enabledPrintDocument":true,"enabledAnnotate":true,"enabledViewParticipantList":true,"enabledViewThumbnails":true,"enabledRemoteControl":true,"enabledViewAnyDocument":true,"enabledViewAnyPage":true,"enabledContactOperatorPrivately":true,"enabledChatHost":true,"enabledChatPresenter":true,"enabledChatOtherParticipants":true},"registration":{"autoAcceptRequest":true,"requireFirstName":true,"requireLastName":true,"requireEmail":true,"requireJobTitle":true,"requireCompanyName":true,"requireAddress1":true,"requireAddress2":true,"requireCity":true,"requireState":true,"requireZipCode":true,"requireCountryRegion":true,"requireWorkPhone":true,"requireFax":true,"maxRegisterNum":0,"customizedQuestions":[{"question":"...","type":"singleLineTextBox","required":true,"maxLength":0,"options":[{"value":"..."}],"rules":[{"condition":"contains","value":"...","result":"approve","matchCase":true}]}],"rules":[{"question":"lastName","condition":"contains","value":"...","result":"approve","order":0,"matchCase":true}]},"integrationTags":["..."],"simultaneousInterpretation":{"enabled":true,"interpreters":[{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"..."}]},"enabledBreakoutSessions":true,"breakoutSessions":[{"name":"...","invitees":["..."]}],"trackingCodes":[{"name":"...","value":"..."}],"enabledAudioWatermark":true,"enabledVisualWatermark":true,"visualWatermarkOpacity":0,"audioConnectionOptions":{"audioConnectionType":"webexAudio","enabledTollFreeCallIn":true,"enabledGlobalCallIn":true,"enabledAudienceCallBack":true,"entryAndExitTone":"beep","allowHostToUnmuteParticipants":true,"allowAttendeeToUnmuteSelf":true,"muteAttendeeUponEntry":true},"requireAttendeeLogin":true,"restrictToInvitees":true,"enabledLiveStream":true,"liveStream":{"destination":"...","rtmpUrl":"...","streamUrl":"...","layoutWithoutSharedContent":"grid","layoutWithSharedContent":"stack","allowChangeLayoutInMeeting":true,"followStageLayoutWhenSynced":true,"resolution":"..."}}'

@app.command("create", short_help="Create a Meeting.")
def create(
    adhoc: bool = typer.Option(None, "--adhoc/--no-adhoc", help="Whether or not to create an ad-hoc meeting for the room specified by `roomId`. When `true`, `roomId` is required."),
    room_id: str = typer.Option(None, "--room-id", help="Unique identifier for the Webex space which the meeting is to be associated with. It can be retrieved by [List Rooms](/docs/api/v1/rooms/list-rooms). `roomId` is required when `adhoc` is `true`. When `roomId` is specified, the parameter `hostEmail` will be ignored."),
    template_id: str = typer.Option(None, "--template-id", help="Unique identifier for meeting template. Please note that `start` and `end` are optional when `templateId` is specified. The list of meeting templates that is available for the authenticated user can be retrieved from [List Meeting Templates](/docs/api/v1/meetings/list-meeting-templates). This..."),
    title: str = typer.Option(None, "--title", help="(required) Meeting title. The title can be a maximum of 128 characters long. The default value for an ad-hoc meeting is the user's name if not specified."),
    agenda: str = typer.Option(None, "--agenda", help="Meeting agenda. The agenda can be a maximum of 1300 characters long."),
    password: str = typer.Option(None, "--password", help="Meeting password. Must conform to the site's password complexity settings. Read [password management](https://help.webex.com/en-us/zrupm6/Manage-Security-Options-for-Your-Site-in-Webex-Site-Administration) for details. If not specified, a random password conforming to the site's password rules will..."),
    start: str = typer.Option(None, "--start", help="(required) Date and time for the start of meeting in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `start` cannot be before current date and time or after `end`. Duration between `start` and `end` cannot be shorter than 10 minutes or longer than 23 hours 59 minutes. Please note that..."),
    end: str = typer.Option(None, "--end", help="(required) Date and time for the end of meeting in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `end` cannot be before current date and time or before `start`. Duration between `start` and `end` cannot be shorter than 10 minutes or longer than 23 hours 59 minutes. Please note that..."),
    timezone: str = typer.Option(None, "--timezone", help="[Time zone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) in which the meeting was originally scheduled (conforming with the [IANA time zone database](https://www.iana.org/time-zones)). The default value for an ad-hoc meeting is `UTC` and the user's input value will be ignored."),
    recurrence: str = typer.Option(None, "--recurrence", help="Meeting series recurrence rule (conforming with [RFC 2445](https://www.ietf.org/rfc/rfc2445.txt)), applying only to meeting series. It doesn't apply to a scheduled meeting or an ended or ongoing meeting instance. This parameter is ignored for an ad-hoc meeting. Multiple days or dates for monthly or..."),
    enabled_auto_record_meeting: bool = typer.Option(None, "--enabled-auto-record-meeting/--no-enabled-auto-record-meeting", help="Whether or not meeting is recorded automatically."),
    allow_any_user_to_be_co_host: bool = typer.Option(None, "--allow-any-user-to-be-co-host/--no-allow-any-user-to-be-co-host", help="Whether or not to allow any attendee with a host account on the target site to become a cohost when joining the meeting. The target site is specified by `siteUrl` parameter when creating the meeting; if not specified, it's the user's preferred site. The default value for an ad-hoc meeting is `true`..."),
    enabled_join_before_host: bool = typer.Option(None, "--enabled-join-before-host/--no-enabled-join-before-host", help="Whether or not to allow any attendee to join the meeting before the host joins the meeting. The default value for an ad-hoc meeting is `true` and the user's input value will be ignored."),
    enable_connect_audio_before_host: bool = typer.Option(None, "--enable-connect-audio-before-host/--no-enable-connect-audio-before-host", help="Whether or not to allow any attendee to connect audio in the meeting before the host joins the meeting. This attribute is only applicable if the `enabledJoinBeforeHost` attribute is set to true. The default value for an ad-hoc meeting is `true` and the user's input value will be ignored."),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help="Number of minutes an attendee can join the meeting before the meeting start time and the host joins. This attribute is only applicable if the `enabledJoinBeforeHost` attribute is set to true. Valid options for a meeting are `0`, `5`, `10`, and `15`, and valid options for a webinar are `0`, `15`,..."),
    exclude_password: bool = typer.Option(None, "--exclude-password/--no-exclude-password", help="Whether or not to exclude the meeting password from the email invitation. This parameter is ignored for an ad-hoc meeting."),
    public_meeting: bool = typer.Option(None, "--public-meeting/--no-public-meeting", help="Whether or not to allow the meeting to be listed on the public calendar. The default value for an ad-hoc meeting is `false` and the user's input value will be ignored."),
    reminder_time: str = typer.Option(None, "--reminder-time", help="The number of minutes before the meeting begins, that an email reminder is sent to the host. This parameter is ignored for an ad-hoc meeting."),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help="Choices: allowJoin, allowJoinWithLobby, blockFromJoin"),
    session_type_id: str = typer.Option(None, "--session-type-id", help="Unique identifier for a meeting session type for the user. This attribute is required when scheduling a webinar meeting. All available meeting session types enabled for the user can be retrieved using the [List Meeting Session Types](/docs/api/v1/meetings/list-meeting-session-types) API."),
    scheduled_type: str = typer.Option(None, "--scheduled-type", help="Choices: meeting, webinar, personalRoomMeeting"),
    enabled_webcast_view: bool = typer.Option(None, "--enabled-webcast-view/--no-enabled-webcast-view", help="Whether or not webcast view is enabled. This parameter is ignored for an ad-hoc meeting."),
    panelist_password: str = typer.Option(None, "--panelist-password", help="Password for panelists of a webinar meeting. Must conform to the site's password complexity settings. Read [password management](https://help.webex.com/en-us/zrupm6/Manage-Security-Options-for-Your-Site-in-Webex-Site-Administration) for details. If not specified, a random password conforming to the..."),
    enable_automatic_lock: bool = typer.Option(None, "--enable-automatic-lock/--no-enable-automatic-lock", help="Whether or not to automatically lock the meeting after it starts. The default value for an ad-hoc meeting is `false` and the user's input value will be ignored."),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help="The number of minutes after the meeting begins, for automatically locking it. The default value for an ad-hoc meeting is null and the user's input value will be ignored."),
    allow_first_user_to_be_co_host: bool = typer.Option(None, "--allow-first-user-to-be-co-host/--no-allow-first-user-to-be-co-host", help="Whether or not to allow the first attendee of the meeting with a host account on the target site to become a cohost. The target site is specified by `siteUrl` parameter when creating the meeting; if not specified, it's user's preferred site. The default value for an ad-hoc meeting is `false` and..."),
    allow_authenticated_devices: bool = typer.Option(None, "--allow-authenticated-devices/--no-allow-authenticated-devices", help="Whether or not to allow authenticated video devices in the meeting's organization to start or join the meeting without a prompt. The default value for an ad-hoc meeting is `true` and the user's input value will be ignored."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether or not to send emails to host and invitees. It is an optional field and default value is true. The default value for an ad-hoc meeting is `false` and the user's input value will be ignored."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin-level scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the meeting is created on. If not specified, the meeting is created on user's preferred site. All available Webex sites and preferred site of the user can be retrieved by `Get Site List` API."),
    enabled_breakout_sessions: bool = typer.Option(None, "--enabled-breakout-sessions/--no-enabled-breakout-sessions", help="Whether or not breakout sessions are enabled."),
    enabled_audio_watermark: bool = typer.Option(None, "--enabled-audio-watermark/--no-enabled-audio-watermark", help="Whether or not the audio watermark is enabled. If it's `true`, `scheduledType` equals or defaults to `meeting`, and `audioConnectionOptions.audioConnectionType` equals `VoIP`, the audio for this meeting will have a watermark. In this case, a unique identifier is embedded into the audio that plays..."),
    enabled_visual_watermark: bool = typer.Option(None, "--enabled-visual-watermark/--no-enabled-visual-watermark", help="Whether or not the visual watermark is enabled. If it's `true`, the video for this meeting will have a watermark. In this case, Webex superimposes a watermark image pattern on top of the meeting video and shared content to deter participants from leaking meeting information. Each participant..."),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help="Opacity level for the visual watermark. The value must be between 5 and 80, inclusive. A smaller value means less distraction for meeting participants, while a larger value shows a clearer watermark. It's supported when `enabledVisualWatermark` is `true`."),
    require_attendee_login: bool = typer.Option(None, "--require-attendee-login/--no-require-attendee-login", help="Require attendees to sign in before joining the webinar. This option works when the value of `scheduledType` attribute is `webinar`. Please note that `requireAttendeeLogin` cannot be set if someone has already registered for the webinar."),
    restrict_to_invitees: bool = typer.Option(None, "--restrict-to-invitees/--no-restrict-to-invitees", help="Restrict webinar to invited attendees only. This option works when the registration option is disabled and the value of `scheduledType` attribute is `webinar`. Please note that `restrictToInvitees` cannot be set to `true` if `requireAttendeeLogin` is `false`."),
    enabled_live_stream: bool = typer.Option(None, "--enabled-live-stream/--no-enabled-live-stream", help="Whether or not live streaming is enabled. If it's enabled, the `liveStream` must be specified. The RTMP streaming specified by `liveStream.rtmpUrl` can be started and viewed during the meeting without any ad-hoc settings."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Meeting.\n\n\b\nExample: wxcli meetings create --title TITLE --start START --end END\n\n\b\nExample --json-body: '{"title":"...","start":"...","end":"...","adhoc":true,"roomId":"...","templateId":"...","agenda":"...","password":"...","timezone":"...","recurrence":"...","enabledAutoRecordMeeting":true,"allowAnyUserToBeCoHost":true,"enabledJoinBeforeHost":true,"enableConnectAudioBeforeHost":true,"joinBeforeHostMinutes":0,"excludePassword":true,"publicMeeting":true,"reminderTime":0,"unlockedMeetingJoinSecurity":"allowJoin","sessionTypeId":0,"scheduledType":"meeting","enabledWebcastView":true,"panelistPassword":"...","enableAutomaticLock":true,"automaticLockMinutes":0,"allowFirstUserToBeCoHost":true,"allowAuthenticatedDevices":true,"invitees":[{"email":"...","displayName":"...","coHost":true,"panelist":true}],"sendEmail":true,"hostEmail":"...","siteUrl":"...","meetingOptions":{"enabledChat":true,"enabledVideo":true,"enabledPolling":true,"enabledNote":true,"noteType":"allowAll","enabledFileTransfer":true,"enabledUCFRichMedia":true},"attendeePrivileges":{"enabledShareContent":true,"enabledSaveDocument":true,"enabledPrintDocument":true,"enabledAnnotate":true,"enabledViewParticipantList":true,"enabledViewThumbnails":true,"enabledRemoteControl":true,"enabledViewAnyDocument":true,"enabledViewAnyPage":true,"enabledContactOperatorPrivately":true,"enabledChatHost":true,"enabledChatPresenter":true,"enabledChatOtherParticipants":true},"registration":{"autoAcceptRequest":true,"requireFirstName":true,"requireLastName":true,"requireEmail":true,"requireJobTitle":true,"requireCompanyName":true,"requireAddress1":true,"requireAddress2":true,"requireCity":true,"requireState":true,"requireZipCode":true,"requireCountryRegion":true,"requireWorkPhone":true,"requireFax":true,"maxRegisterNum":0,"customizedQuestions":[{"question":"...","type":"singleLineTextBox","required":true,"maxLength":0,"options":[{"value":"..."}],"rules":[{"condition":"contains","value":"...","result":"approve","matchCase":true}]}],"rules":[{"question":"lastName","condition":"contains","value":"...","result":"approve","order":0,"matchCase":true}]},"integrationTags":["..."],"simultaneousInterpretation":{"enabled":true,"interpreters":[{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"..."}]},"enabledBreakoutSessions":true,"breakoutSessions":[{"name":"...","invitees":["..."]}],"trackingCodes":[{"name":"...","value":"..."}],"enabledAudioWatermark":true,"enabledVisualWatermark":true,"visualWatermarkOpacity":0,"audioConnectionOptions":{"audioConnectionType":"webexAudio","enabledTollFreeCallIn":true,"enabledGlobalCallIn":true,"enabledAudienceCallBack":true,"entryAndExitTone":"beep","allowHostToUnmuteParticipants":true,"allowAttendeeToUnmuteSelf":true,"muteAttendeeUponEntry":true},"requireAttendeeLogin":true,"restrictToInvitees":true,"enabledLiveStream":true,"liveStream":{"destination":"...","rtmpUrl":"...","streamUrl":"...","layoutWithoutSharedContent":"grid","layoutWithSharedContent":"stack","allowChangeLayoutInMeeting":true,"followStageLayoutWhenSynced":true,"resolution":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-meetings", short_help="Get a Meeting.")
def show_meetings(
    meeting_id: str = typer.Argument(help="UUID, from: wxcli meetings list-meetings"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting.\n\n\b\nExample: wxcli meetings show-meetings MEETING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"title":"...","agenda":"...","password":"...","start":"...","end":"...","timezone":"...","recurrence":"...","enabledAutoRecordMeeting":true,"allowAnyUserToBeCoHost":true,"enabledJoinBeforeHost":true,"enableConnectAudioBeforeHost":true,"joinBeforeHostMinutes":0,"excludePassword":true,"publicMeeting":true,"reminderTime":0,"unlockedMeetingJoinSecurity":"allowJoin","sessionTypeId":0,"enabledWebcastView":true,"panelistPassword":"...","enableAutomaticLock":true,"automaticLockMinutes":0,"allowFirstUserToBeCoHost":true,"allowAuthenticatedDevices":true,"sendEmail":true,"hostEmail":"...","meetingOptions":{"enabledChat":true,"enabledVideo":true,"enabledPolling":true,"enabledNote":true,"noteType":"allowAll","enabledFileTransfer":true,"enabledUCFRichMedia":true},"attendeePrivileges":{"enabledShareContent":true,"enabledSaveDocument":true,"enabledPrintDocument":true,"enabledAnnotate":true,"enabledViewParticipantList":true,"enabledViewThumbnails":true,"enabledRemoteControl":true,"enabledViewAnyDocument":true,"enabledViewAnyPage":true,"enabledContactOperatorPrivately":true,"enabledChatHost":true,"enabledChatPresenter":true,"enabledChatOtherParticipants":true},"integrationTags":["..."],"enabledBreakoutSessions":true,"trackingCodes":[{"name":"...","value":"..."}],"enabledAudioWatermark":true,"enabledVisualWatermark":true,"visualWatermarkOpacity":0,"audioConnectionOptions":{"audioConnectionType":"webexAudio","enabledTollFreeCallIn":true,"enabledGlobalCallIn":true,"enabledAudienceCallBack":true,"entryAndExitTone":"beep","allowHostToUnmuteParticipants":true,"allowAttendeeToUnmuteSelf":true,"muteAttendeeUponEntry":true},"requireAttendeeLogin":true,"restrictToInvitees":true,"enabledLiveStream":true,"liveStream":{"destination":"...","rtmpUrl":"...","streamUrl":"...","layoutWithoutSharedContent":"grid","layoutWithSharedContent":"stack","allowChangeLayoutInMeeting":true,"followStageLayoutWhenSynced":true,"resolution":"..."}}'

@app.command("update", short_help="Update a Meeting.")
def update(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    title: str = typer.Option(None, "--title", help="Meeting title. The title can be a maximum of 128 characters long."),
    agenda: str = typer.Option(None, "--agenda", help="Meeting agenda. The agenda can be a maximum of 1300 characters long."),
    password: str = typer.Option(None, "--password", help="Meeting password. Must conform to the site's password complexity settings. Read [password management](https://help.webex.com/en-us/zrupm6/Manage-Security-Options-for-Your-Site-in-Webex-Site-Administration) for details."),
    start: str = typer.Option(None, "--start", help="Date and time for the start of meeting in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `start` cannot be before current date and time or after `end`. Duration between `start` and `end` cannot be shorter than 10 minutes or longer than 23 hours 59 minutes. Refer to the..."),
    end: str = typer.Option(None, "--end", help="Date and time for the end of meeting in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `end` cannot be before current date and time or before `start`. Duration between `start` and `end` cannot be shorter than 10 minutes or longer than 23 hours 59 minutes. Refer to the..."),
    timezone: str = typer.Option(None, "--timezone", help="[Time zone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) in which the meeting was originally scheduled (conforming with the [IANA time zone database](https://www.iana.org/time-zones))."),
    recurrence: str = typer.Option(None, "--recurrence", help="Meeting series recurrence rule (conforming with [RFC 2445](https://www.ietf.org/rfc/rfc2445.txt)). Applies only to a recurring meeting series, not to a meeting series with only one scheduled meeting. Multiple days or dates for monthly or yearly `recurrence` rule are not supported, only the first..."),
    enabled_auto_record_meeting: bool = typer.Option(None, "--enabled-auto-record-meeting/--no-enabled-auto-record-meeting", help="Whether or not meeting is recorded automatically."),
    allow_any_user_to_be_co_host: bool = typer.Option(None, "--allow-any-user-to-be-co-host/--no-allow-any-user-to-be-co-host", help="Whether or not to allow any attendee with a host account on the target site to become a cohost when joining the meeting. The target site is specified by `siteUrl` parameter when creating the meeting; if not specified, it's user's preferred site."),
    enabled_join_before_host: bool = typer.Option(None, "--enabled-join-before-host/--no-enabled-join-before-host", help="Whether or not to allow any attendee to join the meeting before the host joins the meeting."),
    enable_connect_audio_before_host: bool = typer.Option(None, "--enable-connect-audio-before-host/--no-enable-connect-audio-before-host", help="Whether or not to allow any attendee to connect audio in the meeting before the host joins the meeting. This attribute is only applicable if the `enabledJoinBeforeHost` attribute is set to true."),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help="Number of minutes an attendee can join the meeting before the meeting start time and the host joins. Only applicable if the `enabledJoinBeforeHost` attribute is set to true. Valid options for a meeting are `0`, `5`, `10`, and `15`, and valid options for a webinar are `0`, `15`, `30`, `45`, and..."),
    exclude_password: bool = typer.Option(None, "--exclude-password/--no-exclude-password", help="Whether or not to exclude the meeting password from the email invitation."),
    public_meeting: bool = typer.Option(None, "--public-meeting/--no-public-meeting", help="Whether or not to allow the meeting to be listed on the public calendar."),
    reminder_time: str = typer.Option(None, "--reminder-time", help="The number of minutes before the meeting begins, that an email reminder is sent to the host."),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help="Choices: allowJoin, allowJoinWithLobby, blockFromJoin"),
    session_type_id: str = typer.Option(None, "--session-type-id", help="Unique identifier for a meeting session type for the user. This attribute is required while scheduling webinar meeting. All available meeting session types enabled for the user can be retrieved by [List Meeting Session Types](/docs/api/v1/meetings/list-meeting-session-types) API."),
    enabled_webcast_view: bool = typer.Option(None, "--enabled-webcast-view/--no-enabled-webcast-view", help="Whether or not webcast view is enabled."),
    panelist_password: str = typer.Option(None, "--panelist-password", help="Password for panelists of a webinar meeting. Must conform to the site's password complexity settings. Read [password management](https://help.webex.com/en-us/zrupm6/Manage-Security-Options-for-Your-Site-in-Webex-Site-Administration) for details. If not specified, a random password conforming to the..."),
    enable_automatic_lock: bool = typer.Option(None, "--enable-automatic-lock/--no-enable-automatic-lock", help="Whether or not to automatically lock the meeting after it starts."),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help="The number of minutes after the meeting begins, for automatically locking it."),
    allow_first_user_to_be_co_host: bool = typer.Option(None, "--allow-first-user-to-be-co-host/--no-allow-first-user-to-be-co-host", help="Whether or not to allow the first attendee of the meeting with a host account on the target site to become a cohost. The target site is specified by `siteUrl` parameter when creating the meeting; if not specified, it's user's preferred site."),
    allow_authenticated_devices: bool = typer.Option(None, "--allow-authenticated-devices/--no-allow-authenticated-devices", help="Whether or not to allow authenticated video devices in the meeting's organization to start or join the meeting without a prompt."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether or not to send emails to host and invitees. It is an optional field and default value is true."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin-level scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host. The field is not editable and is only used to update a..."),
    enabled_breakout_sessions: bool = typer.Option(None, "--enabled-breakout-sessions/--no-enabled-breakout-sessions", help="Whether or not breakout sessions are enabled. If the value of `enabledBreakoutSessions` is false, users can not set breakout sessions. If the value of `enabledBreakoutSessions` is true, users can update breakout sessions using the [Update Breakout..."),
    enabled_audio_watermark: bool = typer.Option(None, "--enabled-audio-watermark/--no-enabled-audio-watermark", help="Whether or not the audio watermark is enabled. If it's `true`, `scheduledType` equals or defaults to `meeting`, and `audioConnectionOptions.audioConnectionType` equals `VoIP`, the audio for this meeting will have a watermark. In this case, a unique identifier is embedded into the audio that plays..."),
    enabled_visual_watermark: bool = typer.Option(None, "--enabled-visual-watermark/--no-enabled-visual-watermark", help="Whether or not the visual watermark is enabled. If it's `true`, the video for this meeting will have a watermark. In this case, Webex superimposes a watermark image pattern on top of the meeting video and shared content to deter participants from leaking meeting information. Each participant..."),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help="Opacity level for the visual watermark. The value must be between 5 and 80, inclusive. A smaller value means less distraction for meeting participants, while a larger value shows a clearer watermark. It's supported when `enabledVisualWatermark` is `true`."),
    require_attendee_login: bool = typer.Option(None, "--require-attendee-login/--no-require-attendee-login", help="Require attendees to sign in before joining the webinar. This option works when the value of `scheduledType` attribute is `webinar`. Please note that `requireAttendeeLogin` cannot be set if someone has already registered for the webinar."),
    restrict_to_invitees: bool = typer.Option(None, "--restrict-to-invitees/--no-restrict-to-invitees", help="Restrict webinar to invited attendees only. This option works when the registration option is disabled and the value of `scheduledType` attribute is `webinar`. Please note that `restrictToInvitees` cannot be set to `true` if `requireAttendeeLogin` is `false`."),
    enabled_live_stream: bool = typer.Option(None, "--enabled-live-stream/--no-enabled-live-stream", help="Whether or not live streaming is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Meeting.\n\n\b\nExample: wxcli meetings update MEETING_ID\n\n\b\nExample --json-body: '{"title":"...","agenda":"...","password":"...","start":"...","end":"...","timezone":"...","recurrence":"...","enabledAutoRecordMeeting":true,"allowAnyUserToBeCoHost":true,"enabledJoinBeforeHost":true,"enableConnectAudioBeforeHost":true,"joinBeforeHostMinutes":0,"excludePassword":true,"publicMeeting":true,"reminderTime":0,"unlockedMeetingJoinSecurity":"allowJoin","sessionTypeId":0,"enabledWebcastView":true,"panelistPassword":"...","enableAutomaticLock":true,"automaticLockMinutes":0,"allowFirstUserToBeCoHost":true,"allowAuthenticatedDevices":true,"sendEmail":true,"hostEmail":"...","meetingOptions":{"enabledChat":true,"enabledVideo":true,"enabledPolling":true,"enabledNote":true,"noteType":"allowAll","enabledFileTransfer":true,"enabledUCFRichMedia":true},"attendeePrivileges":{"enabledShareContent":true,"enabledSaveDocument":true,"enabledPrintDocument":true,"enabledAnnotate":true,"enabledViewParticipantList":true,"enabledViewThumbnails":true,"enabledRemoteControl":true,"enabledViewAnyDocument":true,"enabledViewAnyPage":true,"enabledContactOperatorPrivately":true,"enabledChatHost":true,"enabledChatPresenter":true,"enabledChatOtherParticipants":true},"integrationTags":["..."],"enabledBreakoutSessions":true,"trackingCodes":[{"name":"...","value":"..."}],"enabledAudioWatermark":true,"enabledVisualWatermark":true,"visualWatermarkOpacity":0,"audioConnectionOptions":{"audioConnectionType":"webexAudio","enabledTollFreeCallIn":true,"enabledGlobalCallIn":true,"enabledAudienceCallBack":true,"entryAndExitTone":"beep","allowHostToUnmuteParticipants":true,"allowAttendeeToUnmuteSelf":true,"muteAttendeeUponEntry":true},"requireAttendeeLogin":true,"restrictToInvitees":true,"enabledLiveStream":true,"liveStream":{"destination":"...","rtmpUrl":"...","streamUrl":"...","layoutWithoutSharedContent":"grid","layoutWithSharedContent":"stack","allowChangeLayoutInMeeting":true,"followStageLayoutWhenSynced":true,"resolution":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    if json_body:
        body = load_json_body(json_body)
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": meeting_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_MEETINGS = '{"title":"...","agenda":"...","password":"...","start":"...","end":"...","timezone":"...","recurrence":"...","enabledAutoRecordMeeting":true,"allowAnyUserToBeCoHost":true,"enabledJoinBeforeHost":true,"enableConnectAudioBeforeHost":true,"joinBeforeHostMinutes":0,"excludePassword":true,"publicMeeting":true,"reminderTime":0,"unlockedMeetingJoinSecurity":"allowJoin","sessionTypeId":0,"enabledWebcastView":true,"panelistPassword":"...","enableAutomaticLock":true,"automaticLockMinutes":0,"allowFirstUserToBeCoHost":true,"allowAuthenticatedDevices":true,"sendEmail":true,"hostEmail":"...","meetingOptions":{"enabledChat":true,"enabledVideo":true,"enabledPolling":true,"enabledNote":true,"noteType":"allowAll","enabledFileTransfer":true,"enabledUCFRichMedia":true},"attendeePrivileges":{"enabledShareContent":true,"enabledSaveDocument":true,"enabledPrintDocument":true,"enabledAnnotate":true,"enabledViewParticipantList":true,"enabledViewThumbnails":true,"enabledRemoteControl":true,"enabledViewAnyDocument":true,"enabledViewAnyPage":true,"enabledContactOperatorPrivately":true,"enabledChatHost":true,"enabledChatPresenter":true,"enabledChatOtherParticipants":true},"integrationTags":["..."],"enabledBreakoutSessions":true,"trackingCodes":[{"name":"...","value":"..."}],"enabledAudioWatermark":true,"enabledVisualWatermark":true,"visualWatermarkOpacity":0,"audioConnectionOptions":{"audioConnectionType":"webexAudio","enabledTollFreeCallIn":true,"enabledGlobalCallIn":true,"enabledAudienceCallBack":true,"entryAndExitTone":"beep","allowHostToUnmuteParticipants":true,"allowAttendeeToUnmuteSelf":true,"muteAttendeeUponEntry":true},"requireAttendeeLogin":true,"restrictToInvitees":true,"enabledLiveStream":true,"liveStream":{"destination":"...","rtmpUrl":"...","streamUrl":"...","layoutWithoutSharedContent":"grid","layoutWithSharedContent":"stack","allowChangeLayoutInMeeting":true,"followStageLayoutWhenSynced":true,"resolution":"..."}}'

@app.command("update-meetings", short_help="Patch a Meeting.")
def update_meetings(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    title: str = typer.Option(None, "--title", help="Meeting title. The title can be a maximum of 128 characters long."),
    agenda: str = typer.Option(None, "--agenda", help="Meeting agenda. The agenda can be a maximum of 1300 characters long. It can be specified `null` so that it becomes null and hidden from the response after the patch."),
    password: str = typer.Option(None, "--password", help="Meeting password. Must conform to the site's password complexity settings. Read [password management](https://help.webex.com/en-us/zrupm6/Manage-Security-Options-for-Your-Site-in-Webex-Site-Administration) for details."),
    start: str = typer.Option(None, "--start", help="Date and time for the start of meeting in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `start` cannot be before current date and time or after `end`. Duration between `start` and `end` cannot be shorter than 10 minutes or longer than 23 hours 59 minutes. Refer to the..."),
    end: str = typer.Option(None, "--end", help="Date and time for the end of meeting in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `end` cannot be before current date and time or before `start`. Duration between `start` and `end` cannot be shorter than 10 minutes or longer than 23 hours 59 minutes. Refer to the..."),
    timezone: str = typer.Option(None, "--timezone", help="[Time zone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) in which the meeting was originally scheduled (conforming with the [IANA time zone database](https://www.iana.org/time-zones))."),
    recurrence: str = typer.Option(None, "--recurrence", help="Meeting series recurrence rule (conforming with [RFC 2445](https://www.ietf.org/rfc/rfc2445.txt)). Applies only to a recurring meeting series, not to a meeting series with only one scheduled meeting. Multiple days or dates for monthly or yearly `recurrence` rule are not supported, only the first..."),
    enabled_auto_record_meeting: str = typer.Option(None, "--enabled-auto-record-meeting", help="Whether or not meeting is recorded automatically."),
    allow_any_user_to_be_co_host: str = typer.Option(None, "--allow-any-user-to-be-co-host", help="Whether or not to allow any attendee with a host account on the target site to become a cohost when joining the meeting. The target site is specified by `siteUrl` parameter when creating the meeting; if not specified, it's user's preferred site."),
    enabled_join_before_host: str = typer.Option(None, "--enabled-join-before-host", help="Whether or not to allow any attendee to join the meeting before the host joins the meeting."),
    enable_connect_audio_before_host: str = typer.Option(None, "--enable-connect-audio-before-host", help="Whether or not to allow any attendee to connect audio in the meeting before the host joins the meeting. This attribute is only applicable if the `enabledJoinBeforeHost` attribute is set to true."),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help="Number of minutes an attendee can join the meeting before the meeting start time and the host joins. Only applicable if the `enabledJoinBeforeHost` attribute is set to true. Valid options for a meeting are `0`, `5`, `10`, and `15`, and valid options for a webinar are `0`, `15`, `30`, `45`, and..."),
    exclude_password: str = typer.Option(None, "--exclude-password", help="Whether or not to exclude the meeting password from the email invitation."),
    public_meeting: str = typer.Option(None, "--public-meeting", help="Whether or not to allow the meeting to be listed on the public calendar."),
    reminder_time: str = typer.Option(None, "--reminder-time", help="The number of minutes before the meeting begins, that an email reminder is sent to the host."),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help="Choices: allowJoin, allowJoinWithLobby, blockFromJoin"),
    session_type_id: str = typer.Option(None, "--session-type-id", help="Unique identifier for a meeting session type for the user. This attribute is required while scheduling webinar meeting. All available meeting session types enabled for the user can be retrieved by [List Meeting Session Types](/docs/api/v1/meetings/list-meeting-session-types) API."),
    enabled_webcast_view: str = typer.Option(None, "--enabled-webcast-view", help="Whether or not webcast view is enabled."),
    panelist_password: str = typer.Option(None, "--panelist-password", help="Password for panelists of a webinar meeting. Must conform to the site's password complexity settings. Read [password management](https://help.webex.com/en-us/zrupm6/Manage-Security-Options-for-Your-Site-in-Webex-Site-Administration) for details. If not specified, a random password conforming to the..."),
    enable_automatic_lock: str = typer.Option(None, "--enable-automatic-lock", help="Whether or not to automatically lock the meeting after it starts."),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help="The number of minutes after the meeting begins, for automatically locking it."),
    allow_first_user_to_be_co_host: str = typer.Option(None, "--allow-first-user-to-be-co-host", help="Whether or not to allow the first attendee of the meeting with a host account on the target site to become a cohost. The target site is specified by `siteUrl` parameter when creating the meeting; if not specified, it's user's preferred site."),
    allow_authenticated_devices: str = typer.Option(None, "--allow-authenticated-devices", help="Whether or not to allow authenticated video devices in the meeting's organization to start or join the meeting without a prompt."),
    send_email: str = typer.Option(None, "--send-email", help="Whether or not to send emails to host and invitees. It is an optional field and default value is true."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin-level scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host. The field is not editable and is only used to patch a..."),
    enabled_breakout_sessions: str = typer.Option(None, "--enabled-breakout-sessions", help="Whether or not breakout sessions are enabled. If the value of `enabledBreakoutSessions` is false, users can not set breakout sessions. If the value of `enabledBreakoutSessions` is true, users can update breakout sessions using the [Update Breakout..."),
    enabled_audio_watermark: str = typer.Option(None, "--enabled-audio-watermark", help="Whether or not the audio watermark is enabled. If it's `true`, `scheduledType` equals or defaults to `meeting`, and `audioConnectionOptions.audioConnectionType` equals `VoIP`, the audio for this meeting will have a watermark. In this case, a unique identifier is embedded into the audio that plays..."),
    enabled_visual_watermark: str = typer.Option(None, "--enabled-visual-watermark", help="Whether or not the visual watermark is enabled. If it's `true`, the video for this meeting will have a watermark. In this case, Webex superimposes a watermark image pattern on top of the meeting video and shared content to deter participants from leaking meeting information. Each participant..."),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help="Opacity level for the visual watermark. The value must be between 5 and 80, inclusive. A smaller value means less distraction for meeting participants, while a larger value shows a clearer watermark. It's supported when `enabledVisualWatermark` is `true`."),
    require_attendee_login: str = typer.Option(None, "--require-attendee-login", help="Require attendees to sign in before joining the webinar. This option works when the value of `scheduledType` attribute is `webinar`. Please note that `requireAttendeeLogin` cannot be set if someone has already registered for the webinar."),
    restrict_to_invitees: str = typer.Option(None, "--restrict-to-invitees", help="Restrict webinar to invited attendees only. This option works when the registration option is disabled and the value of `scheduledType` attribute is `webinar`. Please note that `restrictToInvitees` cannot be set to `true` if `requireAttendeeLogin` is `false`."),
    enabled_live_stream: str = typer.Option(None, "--enabled-live-stream", help="Whether or not live streaming is enabled."),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Patch a Meeting.\n\n\b\nExample: wxcli meetings update-meetings MEETING_ID\n\n\b\nExample --json-body: '{"title":"...","agenda":"...","password":"...","start":"...","end":"...","timezone":"...","recurrence":"...","enabledAutoRecordMeeting":true,"allowAnyUserToBeCoHost":true,"enabledJoinBeforeHost":true,"enableConnectAudioBeforeHost":true,"joinBeforeHostMinutes":0,"excludePassword":true,"publicMeeting":true,"reminderTime":0,"unlockedMeetingJoinSecurity":"allowJoin","sessionTypeId":0,"enabledWebcastView":true,"panelistPassword":"...","enableAutomaticLock":true,"automaticLockMinutes":0,"allowFirstUserToBeCoHost":true,"allowAuthenticatedDevices":true,"sendEmail":true,"hostEmail":"...","meetingOptions":{"enabledChat":true,"enabledVideo":true,"enabledPolling":true,"enabledNote":true,"noteType":"allowAll","enabledFileTransfer":true,"enabledUCFRichMedia":true},"attendeePrivileges":{"enabledShareContent":true,"enabledSaveDocument":true,"enabledPrintDocument":true,"enabledAnnotate":true,"enabledViewParticipantList":true,"enabledViewThumbnails":true,"enabledRemoteControl":true,"enabledViewAnyDocument":true,"enabledViewAnyPage":true,"enabledContactOperatorPrivately":true,"enabledChatHost":true,"enabledChatPresenter":true,"enabledChatOtherParticipants":true},"integrationTags":["..."],"enabledBreakoutSessions":true,"trackingCodes":[{"name":"...","value":"..."}],"enabledAudioWatermark":true,"enabledVisualWatermark":true,"visualWatermarkOpacity":0,"audioConnectionOptions":{"audioConnectionType":"webexAudio","enabledTollFreeCallIn":true,"enabledGlobalCallIn":true,"enabledAudienceCallBack":true,"entryAndExitTone":"beep","allowHostToUnmuteParticipants":true,"allowAttendeeToUnmuteSelf":true,"muteAttendeeUponEntry":true},"requireAttendeeLogin":true,"restrictToInvitees":true,"enabledLiveStream":true,"liveStream":{"destination":"...","rtmpUrl":"...","streamUrl":"...","layoutWithoutSharedContent":"grid","layoutWithSharedContent":"stack","allowChangeLayoutInMeeting":true,"followStageLayoutWhenSynced":true,"resolution":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MEETINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    if json_body:
        body = load_json_body(json_body)
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": meeting_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Meeting.")
def delete(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will delete a meeting that is hosted by that user."),
    send_email: str = typer.Option(None, "--send-email", help="Whether or not to send emails to host and invitees. It is an optional field and default value is true."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting.\n\n\b\nExample: wxcli meetings delete MEETING_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {meeting_id}?", abort=True)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
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
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {meeting_id}")
    else:
        emit({"status": "deleted", "id": meeting_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_JOIN = '{"meetingId":"...","meetingNumber":"...","webLink":"...","joinDirectly":true,"email":"...","displayName":"...","password":"...","expirationMinutes":0,"registrationId":"...","hostEmail":"...","createJoinLinkAsWebLink":true,"createStartLinkAsWebLink":true}'

@app.command("create-join", short_help="Join a Meeting.")
def create_join(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the meeting. This parameter applies to meeting series and scheduled meetings. It doesn't apply to ended or in-progress meeting instances. Please note that currently meeting ID of a scheduled [personal..."),
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number. Applies to meeting series, scheduled meeting, and meeting instances, but not to meeting instances which have ended."),
    web_link: str = typer.Option(None, "--web-link", help="Link to a meeting information page where the meeting client is launched if the meeting is ready to start or join."),
    join_directly: bool = typer.Option(None, "--join-directly/--no-join-directly", help="Whether or not to redirect to `joinLink`. It is an optional field and default value is true."),
    email: str = typer.Option(None, "--email", help="Email address of meeting participant. If `email` is specified, the link is generated for the user of `email`; otherwise, the API returns the link for the user calling the API. `email` is required for a [guest issuer](https://developer.webex.com/docs/guest-issuer)."),
    display_name: str = typer.Option(None, "--display-name", help="Display name of meeting participant. If `displayName` is specified, `email` must be specified as well. If `email` is specified and `displayName` is not, display name is the same as `email`. If neither `displayName` nor `email` is specified, the API returns the link for the user calling the API. The..."),
    password: str = typer.Option(None, "--password", help="Required when the meeting is protected by a password and the current user is not privileged to view it if they are not a host, cohost, or invitee."),
    expiration_minutes: str = typer.Option(None, "--expiration-minutes", help="Expiration duration of `joinLink` in minutes. Must be between 1 and 60."),
    registration_id: str = typer.Option(None, "--registration-id", help="Required when the meeting is webinar-enabled and enabled registration ID."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should be set if the user or application calling the API has the admin on-behalf-of scopes. This parameter is required for a [Service App](/docs/service-apps). It only applies to meetings, not webinars."),
    create_join_link_as_web_link: bool = typer.Option(None, "--create-join-link-as-web-link/--no-create-join-link-as-web-link", help="When `createJoinLinkAsWebLink` is true, the returned `joinLink` is the webLink of the meeting, otherwise, the normal `joinLink` is returned. This parameter is applicable when the option to force the user to log in is set in Control Hub. When true, a user cannot join the meeting by the link directly..."),
    create_start_link_as_web_link: bool = typer.Option(None, "--create-start-link-as-web-link/--no-create-start-link-as-web-link", help="When `createStartLinkAsWebLink` is true, the returned `startLink` is the webLink of the meeting, otherwise, the normal `startLink` is returned. This parameter is applicable when the option to force the user to log in is set in Control Hub. When true, a user cannot start the meeting using the link..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Join a Meeting.\n\n\b\nExample --json-body: '{"meetingId":"...","meetingNumber":"...","webLink":"...","joinDirectly":true,"email":"...","displayName":"...","password":"...","expirationMinutes":0,"registrationId":"...","hostEmail":"...","createJoinLinkAsWebLink":true,"createStartLinkAsWebLink":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_JOIN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/join"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("list-templates", short_help="List Meeting Templates.")
def list_templates(
    template_type: str = typer.Option(None, "--template-type", help="Choices: meeting, webinar"),
    locale: str = typer.Option(None, "--locale", help="Locale for the meeting template objects being requested. If not specified, return meeting templates of the default `en_US` locale. Refer to [Meeting Template Locales](/docs/meetings#meeting-template-locales) for all the locales supported by Webex."),
    is_default: str = typer.Option(None, "--is-default", help="The value is `true` or `false`. If it's `true`, return the default meeting templates; if it's `false`, return the non-default meeting templates. If it's not specified, return both default and non-default meeting templates."),
    is_standard: str = typer.Option(None, "--is-standard", help="The value is `true` or `false`. If it's `true`, return the standard meeting templates; if it's `false`, return the non-standard meeting templates. If it's not specified, return both standard and non-standard meeting templates."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return meeting templates that are available for that user."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meeting templates from. If not specified, the API lists meeting templates from user's preferred site. All available Webex sites and preferred site of the user can be retrieved by `Get Site List` API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Locale', 'locale'), ('Site URL', 'siteUrl'), ('Template Type', 'templateType')], limit=limit)



@app.command("show-templates", short_help="Get a Meeting Template.")
def show_templates(
    template_id: str = typer.Argument(help="from: wxcli meetings list-templates"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return the meeting template that is available for that user."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Template.\n\n\b\nExample: wxcli meetings show-templates TEMPLATE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/templates/{template_id}"
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



@app.command("show-controls", short_help="Get Meeting Control Status.")
def show_controls(
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the meeting. Does not support meeting IDs for a scheduled [personal room](https://help.webex.com/en-us/article/nul0wut/Webex-Personal-Rooms-in-Webex-Meetings) meeting."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Control Status.\n\n\b\nExample: wxcli meetings show-controls --meeting-id MEETING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/controls"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CONTROLS = '{"recordingStarted":true,"recordingPaused":true,"locked":true}'

@app.command("update-controls", short_help="Update Meeting Control Status.")
def update_controls(
    meeting_id: str = typer.Option(..., "--meeting-id", help="Unique identifier for the meeting. Does not support meeting IDs for a scheduled [personal room](https://help.webex.com/en-us/article/nul0wut/Webex-Personal-Rooms-in-Webex-Meetings) meeting."),
    recording_started: bool = typer.Option(None, "--recording-started/--no-recording-started", help="The value can be true or false. true means to start the recording, false to end the recording."),
    recording_paused: bool = typer.Option(None, "--recording-paused/--no-recording-paused", help="The value can be true or false, will be ignored if 'recordingStarted' sets to false, and true to resume the recording only if the recording is paused vise versa."),
    locked: bool = typer.Option(None, "--locked/--no-locked", help="The value is true or false."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Control Status.\n\n\b\nExample: wxcli meetings update-controls --meeting-id MEETING_ID\n\n\b\nExample --json-body: '{"recordingStarted":true,"recordingPaused":true,"locked":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CONTROLS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/controls"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if json_body:
        body = load_json_body(json_body)
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("list-session-types", short_help="List Meeting Session Types.")
def list_session_types(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will list all the meeting session types enabled for the user."),
    site_url: str = typer.Option(None, "--site-url", help="Webex site URL to query. If `siteUrl` is not specified, the users' preferred site will be used. If the authorization token has the admin-level scopes, the admin can set the Webex site URL on behalf of the user specified in the `hostEmail` parameter."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Attendees Capacity', 'attendeesCapacity')], limit=limit)



@app.command("show-session-types", short_help="Get a Meeting Session Type.")
def show_session_types(
    session_type_id: str = typer.Argument(help="from: wxcli meetings list-session-types"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will get a meeting session type with the specified session type ID enabled for the user."),
    site_url: str = typer.Option(None, "--site-url", help="Webex site URL to query. If `siteUrl` is not specified, the users' preferred site will be used. If the authorization token has the admin-level scopes, the admin can set the Webex site URL on behalf of the user specified in the `hostEmail` parameter."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Session Type.\n\n\b\nExample: wxcli meetings show-session-types SESSION_TYPE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/sessionTypes/{session_type_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if site_url is not None:
        params["siteUrl"] = site_url
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-registration", short_help="Get registration form for a meeting.")
def list_registration(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get registration form for a meeting.\n\n\b\nExample: wxcli meetings list-registration MEETING_ID"""
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("customizedQuestions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Question', 'question'), ('Type', 'type'), ('Required', 'required')], limit=limit)



_BODY_SKELETON_UPDATE_REGISTRATION = '{"hostEmail":"...","autoAcceptRequest":true,"requireFirstName":true,"requireLastName":true,"requireEmail":true,"requireJobTitle":true,"requireCompanyName":true,"requireAddress1":true,"requireAddress2":true,"requireCity":true,"requireState":true,"requireZipCode":true,"requireCountryRegion":true,"requireWorkPhone":true,"requireFax":true,"maxRegisterNum":0,"customizedQuestions":[{"question":"...","type":"singleLineTextBox","required":true,"maxLength":0,"options":[{"value":"..."}],"rules":[{"condition":"contains","value":"...","result":"approve","matchCase":true}]}],"rules":[{"question":"lastName","condition":"contains","value":"...","result":"approve","order":0,"matchCase":true}]}'

@app.command("update-registration", short_help="Update Meeting Registration Form.")
def update_registration(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    host_email: str = typer.Option(None, "--host-email", help="- Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return an update for a meeting that is hosted by that user."),
    auto_accept_request: bool = typer.Option(None, "--auto-accept-request/--no-auto-accept-request", help="Whether or not meeting registration requests are accepted automatically."),
    require_first_name: bool = typer.Option(None, "--require-first-name/--no-require-first-name", help="Whether or not a registrant's first name is required for meeting registration. This option must always be `true`."),
    require_last_name: bool = typer.Option(None, "--require-last-name/--no-require-last-name", help="Whether or not a registrant's last name is required for meeting registration. This option must always be `true`."),
    require_email: bool = typer.Option(None, "--require-email/--no-require-email", help="Whether or not a registrant's email is required for meeting registration. This option must always be `true`."),
    require_job_title: bool = typer.Option(None, "--require-job-title/--no-require-job-title", help="Whether or not a registrant's job title is shown or required for meeting registration."),
    require_company_name: bool = typer.Option(None, "--require-company-name/--no-require-company-name", help="Whether or not a registrant's company name is shown or required for meeting registration."),
    require_address1: bool = typer.Option(None, "--require-address1/--no-require-address1", help="Whether or not a registrant's first address field is shown or required for meeting registration."),
    require_address2: bool = typer.Option(None, "--require-address2/--no-require-address2", help="Whether or not a registrant's second address field is shown or required for meeting registration."),
    require_city: bool = typer.Option(None, "--require-city/--no-require-city", help="Whether or not a registrant's city is shown or required for meeting registration."),
    require_state: bool = typer.Option(None, "--require-state/--no-require-state", help="Whether or not a registrant's state is shown or required for meeting registration."),
    require_zip_code: bool = typer.Option(None, "--require-zip-code/--no-require-zip-code", help="Whether or not a registrant's postal code is shown or required for meeting registration."),
    require_country_region: bool = typer.Option(None, "--require-country-region/--no-require-country-region", help="Whether or not a registrant's country or region is shown or required for meeting registration."),
    require_work_phone: bool = typer.Option(None, "--require-work-phone/--no-require-work-phone", help="Whether or not a registrant's work phone number is shown or required for meeting registration."),
    require_fax: bool = typer.Option(None, "--require-fax/--no-require-fax", help="Whether or not a registrant's fax number is shown or required for meeting registration."),
    max_register_num: str = typer.Option(None, "--max-register-num", help="Maximum number of meeting registrations. This only applies to meetings. The maximum number of participants for meetings and webinars, with the limit based on the user capacity and controlled by a toggle at the site level. The default maximum number of participants for webinars is 10000, but the..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Registration Form.\n\n\b\nExample: wxcli meetings update-registration MEETING_ID\n\n\b\nExample --json-body: '{"hostEmail":"...","autoAcceptRequest":true,"requireFirstName":true,"requireLastName":true,"requireEmail":true,"requireJobTitle":true,"requireCompanyName":true,"requireAddress1":true,"requireAddress2":true,"requireCity":true,"requireState":true,"requireZipCode":true,"requireCountryRegion":true,"requireWorkPhone":true,"requireFax":true,"maxRegisterNum":0,"customizedQuestions":[{"question":"...","type":"singleLineTextBox","required":true,"maxLength":0,"options":[{"value":"..."}],"rules":[{"condition":"contains","value":"...","result":"approve","matchCase":true}]}],"rules":[{"question":"lastName","condition":"contains","value":"...","result":"approve","order":0,"matchCase":true}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_REGISTRATION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registration"
    if json_body:
        body = load_json_body(json_body)
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": meeting_id}, output=output, fields=fields)



@app.command("delete-registration", short_help="Delete Meeting Registration Form.")
def delete_registration(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Meeting Registration Form.\n\n\b\nExample: wxcli meetings delete-registration MEETING_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Registration for {meeting_id}?", abort=True)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registration"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {meeting_id}")
    else:
        emit({"status": "deleted", "id": meeting_id}, output=output, fields=fields)



@app.command("list-registrants", short_help="List Meeting Registrants.")
def list_registrants(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    email: str = typer.Option(None, "--email", help="Registrant's email to filter registrants."),
    registration_time_from: str = typer.Option(None, "--registration-time-from", help="The time registrants register a meeting starts from the specified date and time (inclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `registrationTimeFrom` is not specified, it equals `registrationTimeTo` minus 7 days."),
    registration_time_to: str = typer.Option(None, "--registration-time-to", help="The time registrants register a meeting before the specified date and time (exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. If `registrationTimeTo` is not specified, it equals `registrationTimeFrom` plus 7 days. The interval between `registrationTimeFrom` and..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Registrants.\n\n\b\nExample: wxcli meetings list-registrants MEETING_ID"""
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Email', 'email'), ('Status', 'status')], limit=limit)



_BODY_SKELETON_CREATE_REGISTRANTS = '{"firstName":"...","lastName":"...","email":"...","sendEmail":true,"jobTitle":"...","companyName":"...","address1":"...","address2":"...","city":"...","state":"...","zipCode":0,"countryRegion":"...","workPhone":"...","fax":"...","customizedQuestions":[{"questionId":0,"answers":[{"answer":"...","optionId":0}]}]}'

@app.command("create-registrants", short_help="Register a Meeting Registrant.")
def create_registrants(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    first_name: str = typer.Option(None, "--first-name", help="(required) The registrant's first name."),
    last_name: str = typer.Option(None, "--last-name", help="(required) The registrant's last name. (Required)"),
    email: str = typer.Option(None, "--email", help="(required) The registrant's email."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to the registrant. Default: `true`."),
    job_title: str = typer.Option(None, "--job-title", help="The registrant's job title. Registration options define whether or not this is required."),
    company_name: str = typer.Option(None, "--company-name", help="The registrant's company. Registration options define whether or not this is required."),
    address1: str = typer.Option(None, "--address1", help="The registrant's first address line. Registration options define whether or not this is required."),
    address2: str = typer.Option(None, "--address2", help="The registrant's second address line. Registration options define whether or not this is required."),
    city: str = typer.Option(None, "--city", help="The registrant's city name. Registration options define whether or not this is required."),
    state: str = typer.Option(None, "--state", help="The registrant's state. Registration options define whether or not this is required."),
    zip_code: str = typer.Option(None, "--zip-code", help="The registrant's postal code. Registration options define whether or not this is required."),
    country_region: str = typer.Option(None, "--country-region", help="The America is not a country or a specific region. Registration options define whether or not this is required."),
    work_phone: str = typer.Option(None, "--work-phone", help="The registrant's work phone number. Registration options define whether or not this is required."),
    fax: str = typer.Option(None, "--fax", help="The registrant's FAX number. Registration options define whether or not this is required."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Register a Meeting Registrant.\n\n\b\nExample: wxcli meetings create-registrants MEETING_ID --first-name FIRST_NAME --last-name LAST_NAME --email EMAIL\n\n\b\nExample --json-body: '{"firstName":"...","lastName":"...","email":"...","sendEmail":true,"jobTitle":"...","companyName":"...","address1":"...","address2":"...","city":"...","state":"...","zipCode":0,"countryRegion":"...","workPhone":"...","fax":"...","customizedQuestions":[{"questionId":0,"answers":[{"answer":"...","optionId":0}]}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_REGISTRANTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
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



_BODY_SKELETON_CREATE_BULK_INSERT = '{"items":[{"firstName":"...","lastName":"...","email":"...","sendEmail":true,"jobTitle":"...","companyName":"...","address1":"...","address2":"...","city":"...","state":"...","zipCode":0,"countryRegion":"...","workPhone":"...","fax":"...","customizedQuestions":[{"questionId":0,"answers":[{"answer":"...","optionId":0}]}]}]}'

@app.command("create-bulk-insert", short_help="Batch register Meeting Registrants.")
def create_bulk_insert(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch register Meeting Registrants.\n\n\b\nExample: wxcli meetings create-bulk-insert MEETING_ID\n\n\b\nExample --json-body: '{"items":[{"firstName":"...","lastName":"...","email":"...","sendEmail":true,"jobTitle":"...","companyName":"...","address1":"...","address2":"...","city":"...","state":"...","zipCode":0,"countryRegion":"...","workPhone":"...","fax":"...","customizedQuestions":[{"questionId":0,"answers":[{"answer":"...","optionId":0}]}]}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK_INSERT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/bulkInsert"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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



@app.command("show-registrants", short_help="Get Detailed Information for a Meeting Registrant.")
def show_registrants(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    registrant_id: str = typer.Argument(help="UUID, from: wxcli meetings list-registrants"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Detailed Information for a Meeting Registrant.\n\n\b\nExample: wxcli meetings show-registrants MEETING_ID REGISTRANT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/{registrant_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("delete-registrants", short_help="Delete a Meeting Registrant.")
def delete_registrants(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    registrant_id: str = typer.Argument(help="UUID, from: wxcli meetings list-registrants"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Registrant.\n\n\b\nExample: wxcli meetings delete-registrants MEETING_ID REGISTRANT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {registrant_id}?", abort=True)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/{registrant_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {registrant_id}")
    else:
        emit({"status": "deleted", "id": registrant_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_QUERY = '{"emails":["..."],"status":"approved","orderType":"DESC","orderBy":"firstName"}'

@app.command("create-query", short_help="Query Meeting Registrants.")
def create_query(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of registrants in the response, up to 100. The default is 10."),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    status: str = typer.Option(None, "--status", help="Choices: approved, pending, rejected"),
    order_type: str = typer.Option(None, "--order-type", help="Choices: DESC, ASC"),
    order_by: str = typer.Option(None, "--order-by", help="Choices: firstName, lastName, status, email"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Meeting Registrants.\n\n\b\nExample: wxcli meetings create-query MEETING_ID --json-body '{"emails":["..."]}'\n\n\b\nExample --json-body: '{"emails":["..."],"status":"approved","orderType":"DESC","orderBy":"firstName"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_QUERY), indent=2))
        raise typer.Exit(0)
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
        body = load_json_body(json_body)
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



_BODY_SKELETON_CREATE_APPROVE = '{"sendEmail":true,"registrants":[{"id":"..."}]}'

@app.command("create-approve", short_help="Batch Approve Meeting Registrants.")
def create_approve(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to registrants. Default: `true`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Approve Meeting Registrants.\n\n\b\nExample: wxcli meetings create-approve MEETING_ID\n\n\b\nExample --json-body: '{"sendEmail":true,"registrants":[{"id":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_APPROVE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/approve"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
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



_BODY_SKELETON_CREATE_REJECT = '{"sendEmail":true,"registrants":[{"id":"..."}]}'

@app.command("create-reject", short_help="Batch Reject Meeting Registrants.")
def create_reject(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to registrants. Default: `true`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Reject Meeting Registrants.\n\n\b\nExample: wxcli meetings create-reject MEETING_ID\n\n\b\nExample --json-body: '{"sendEmail":true,"registrants":[{"id":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/reject"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
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



_BODY_SKELETON_CREATE_CANCEL = '{"sendEmail":true,"registrants":[{"id":"..."}]}'

@app.command("create-cancel", short_help="Batch Cancel Meeting Registrants.")
def create_cancel(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to registrants. Default: `true`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Cancel Meeting Registrants.\n\n\b\nExample: wxcli meetings create-cancel MEETING_ID\n\n\b\nExample --json-body: '{"sendEmail":true,"registrants":[{"id":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CANCEL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/cancel"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
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



_BODY_SKELETON_CREATE_BULK_DELETE = '{"sendEmail":true,"registrants":[{"id":"..."}]}'

@app.command("create-bulk-delete", short_help="Batch Delete Meeting Registrants.")
def create_bulk_delete(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meeting of the meeting series, i.e. the meeting ready to join or start or the upcoming meeting of the meeting series. If it's `true`, return details for the current scheduled meeting of the series, i.e. the scheduled meeting ready to join or..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true` send email to registrants. Default: `true`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Delete Meeting Registrants.\n\n\b\nExample: wxcli meetings create-bulk-delete MEETING_ID\n\n\b\nExample --json-body: '{"sendEmail":true,"registrants":[{"id":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK_DELETE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/bulkDelete"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
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



_BODY_SKELETON_UPDATE_SIMULTANEOUS_INTERPRETATION = '{"enabled":true,"interpreters":[{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"..."}]}'

@app.command("update-simultaneous-interpretation", short_help="Update Meeting Simultaneous interpretation.")
def update_simultaneous_interpretation(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not simultaneous interpretation is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Simultaneous interpretation.\n\n\b\nExample: wxcli meetings update-simultaneous-interpretation MEETING_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true,"interpreters":[{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SIMULTANEOUS_INTERPRETATION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/simultaneousInterpretation"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": meeting_id}, output=output, fields=fields)



@app.command("list-interpreters", short_help="List Meeting Interpreters.")
def list_interpreters(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will return interpreters of the meeting that is hosted by that user."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Interpreters.\n\n\b\nExample: wxcli meetings list-interpreters MEETING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Language Code1', 'languageCode1'), ('Language Code2', 'languageCode2'), ('Email', 'email')], limit=limit)



_BODY_SKELETON_CREATE_INTERPRETERS = '{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"...","hostEmail":"...","sendEmail":true}'

@app.command("create-interpreters", short_help="Create a Meeting Interpreter.")
def create_interpreters(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    language_code1: str = typer.Option(None, "--language-code1", help="(required) The pair of `languageCode1` and `languageCode2` form a bi-directional simultaneous interpretation language channel. The language codes conform with [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)."),
    language_code2: str = typer.Option(None, "--language-code2", help="(required) The pair of `languageCode1` and `languageCode2` form a bi-directional simultaneous interpretation language channel. The language codes conform with [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)."),
    email: str = typer.Option(None, "--email", help="Email address of meeting interpreter. If not specified, an empty interpreter will be created for this bi-directional language channel, and a specific email can be assigned to this empty interpreter by `Update a Meeting Interpreter` API later. Please note that multiple interpreters with different..."),
    display_name: str = typer.Option(None, "--display-name", help="Display name of meeting interpreter. If the interpreter is already an invitee of the meeting and it has a different display name, that invitee's display name will be overwritten by this attribute."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin on-behalf-of scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true`, send email to the interpreter."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Meeting Interpreter.\n\n\b\nExample: wxcli meetings create-interpreters MEETING_ID --language-code1 LANGUAGE_CODE1 --language-code2 LANGUAGE_CODE2\n\n\b\nExample --json-body: '{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"...","hostEmail":"...","sendEmail":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_INTERPRETERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-interpreters", short_help="Get a Meeting Interpreter.")
def show_interpreters(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    interpreter_id: str = typer.Argument(help="from: wxcli meetings list-interpreters"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for an interpreter of the meeting that is hosted by..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Interpreter.\n\n\b\nExample: wxcli meetings show-interpreters MEETING_ID INTERPRETER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
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



_BODY_SKELETON_UPDATE_INTERPRETERS = '{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"...","hostEmail":"...","sendEmail":true}'

@app.command("update-interpreters", short_help="Update a Meeting Interpreter.")
def update_interpreters(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    interpreter_id: str = typer.Argument(help="from: wxcli meetings list-interpreters"),
    language_code1: str = typer.Option(None, "--language-code1", help="The pair of `languageCode1` and `languageCode2` form a bi-directional simultaneous interpretation language channel. The language codes conform with [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)."),
    language_code2: str = typer.Option(None, "--language-code2", help="The pair of `languageCode1` and `languageCode2` form a bi-directional simultaneous interpretation language channel. The language codes conform with [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)."),
    email: str = typer.Option(None, "--email", help="Email address of meeting interpreter. If not specified, it'll be an empty interpreter for the bi-directional language channel. Please note that multiple interpreters with different emails can be assigned to the same bi-directional language channel, but the same email cannot be assigned to more than..."),
    display_name: str = typer.Option(None, "--display-name", help="Display name of meeting interpreter. If the interpreter is already an invitee of the meeting and it has a different display name, that invitee's display name will be overwritten by this attribute."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin on-behalf-of scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="If `true`, send email to the interpreter."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Meeting Interpreter.\n\n\b\nExample: wxcli meetings update-interpreters MEETING_ID INTERPRETER_ID --language-code1 LANGUAGE_CODE1 --language-code2 LANGUAGE_CODE2\n\n\b\nExample --json-body: '{"languageCode1":"...","languageCode2":"...","email":"...","displayName":"...","hostEmail":"...","sendEmail":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_INTERPRETERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
    if json_body:
        body = load_json_body(json_body)
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": interpreter_id}, output=output, fields=fields)



@app.command("delete-interpreters", short_help="Delete a Meeting Interpreter.")
def delete_interpreters(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    interpreter_id: str = typer.Argument(help="from: wxcli meetings list-interpreters"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. If set, the admin may specify the email of a user in a site they manage and the API will delete an interpreter of the meeting that is hosted by that user."),
    send_email: str = typer.Option(None, "--send-email", help="If `true`, send email to the interpreter."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Interpreter.\n\n\b\nExample: wxcli meetings delete-interpreters MEETING_ID INTERPRETER_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {interpreter_id}?", abort=True)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
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
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {interpreter_id}")
    else:
        emit({"status": "deleted", "id": interpreter_id}, output=output, fields=fields)



@app.command("list-breakout-sessions", short_help="List Meeting Breakout Sessions.")
def list_breakout_sessions(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Breakout Sessions.\n\n\b\nExample: wxcli meetings list-breakout-sessions MEETING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Start Time', 'startTime'), ('End Time', 'endTime')], limit=limit)



_BODY_SKELETON_UPDATE_BREAKOUT_SESSIONS = '{"hostEmail":"...","sendEmail":true,"items":[{"name":"...","invitees":["..."]}]}'

@app.command("update-breakout-sessions", short_help="Update Meeting Breakout Sessions.")
def update_breakout_sessions(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin-level scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether or not to send emails to host and invitees. It is an optional field and default value is true."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Breakout Sessions.\n\n\b\nExample: wxcli meetings update-breakout-sessions MEETING_ID\n\n\b\nExample --json-body: '{"hostEmail":"...","sendEmail":true,"items":[{"name":"...","invitees":["..."]}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_BREAKOUT_SESSIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": meeting_id}, output=output, fields=fields)



@app.command("delete-breakout-sessions", short_help="Delete Meeting Breakout Sessions.")
def delete_breakout_sessions(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    send_email: str = typer.Option(None, "--send-email", help="Whether or not to send emails to host and invitees. It is an optional field and default value is true."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Meeting Breakout Sessions.\n\n\b\nExample: wxcli meetings delete-breakout-sessions MEETING_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Breakout Sessions for {meeting_id}?", abort=True)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    params = {}
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
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {meeting_id}")
    else:
        emit({"status": "deleted", "id": meeting_id}, output=output, fields=fields)



@app.command("list-survey", short_help="Get a Meeting Survey.")
def list_survey(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Survey.\n\n\b\nExample: wxcli meetings list-survey MEETING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/survey"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("questions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Question', 'question'), ('Type', 'type')], limit=limit)



@app.command("list-survey-results", short_help="List Meeting Survey Results.")
def list_survey_results(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Start date and time (inclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format for the meeting objects being requested. `meetingStartTimeFrom` cannot be after `meetingStartTimeTo`. This parameter will be ignored if `meetingId` is the unique identifier for the specific..."),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="End date and time (exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format for the meeting objects being requested. `meetingStartTimeTo` cannot be prior to `meetingStartTimeFrom`. This parameter will be ignored if `meetingId` is the unique identifier for the specific..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Survey Results.\n\n\b\nExample: wxcli meetings list-survey-results MEETING_ID"""
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Survey Name', 'surveyName'), ('Meeting ID', 'meetingId'), ('Email', 'email')], limit=limit)



_BODY_SKELETON_CREATE_SURVEY_LINKS = '{"hostEmail":"...","meetingStartTimeFrom":"...","meetingStartTimeTo":"...","emails":["..."]}'

@app.command("create-survey-links", short_help="Get Meeting Survey Links.")
def create_survey_links(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the admin on-behalf-of scopes. An admin can specify the email of the meeting host who is in a site he manages and the API returns post survey links on behalf of the meeting host."),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Start date and time (inclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format for the meeting objects being requested and conforms with the `timezone` in the request header if specified. `meetingStartTimeFrom` cannot be after `meetingStartTimeTo`. Only applies when..."),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="End date and time (exclusive) in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format for the meeting objects being requested and conforms with the `timezone` in the request header if specified. `meetingStartTimeTo` cannot be prior to `meetingStartTimeFrom`. Only applies when..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Survey Links.\n\n\b\nExample: wxcli meetings create-survey-links MEETING_ID\n\n\b\nExample --json-body: '{"hostEmail":"...","meetingStartTimeFrom":"...","meetingStartTimeTo":"...","emails":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SURVEY_LINKS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/surveyLinks"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("list-invitation-sources", short_help="List Invitation Sources.")
def list_invitation_sources(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Invitation Sources.\n\n\b\nExample: wxcli meetings list-invitation-sources MEETING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/invitationSources"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Source ID', 'sourceId'), ('Source Email', 'sourceEmail'), ('Join Link', 'joinLink')], limit=limit)



_BODY_SKELETON_CREATE_INVITATION_SOURCES = '{"hostEmail":"...","personId":"...","items":[{"sourceId":"...","sourceEmail":"..."}]}'

@app.command("create-invitation-sources", short_help="Create Invitation Sources.")
def create_invitation_sources(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if a user or application calling the API has the admin-level scopes. The admin may specify the email of a user on a site they manage and the API will return meeting participants of the meetings that are hosted by that user."),
    person_id: str = typer.Option(None, "--person-id", help="Unique identifier for the meeting host. Should only be set if the user or application calling the API has the admin-level scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Invitation Sources.\n\n\b\nExample: wxcli meetings create-invitation-sources MEETING_ID\n\n\b\nExample --json-body: '{"hostEmail":"...","personId":"...","items":[{"sourceId":"...","sourceEmail":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_INVITATION_SOURCES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/invitationSources"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if person_id is not None:
            body["personId"] = person_id
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



@app.command("list-tracking-codes", short_help="List Meeting Tracking Codes.")
def list_tracking_codes(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API retrieves the tracking code from. If not specified, the API retrieves the tracking code from the user's preferred site. All available Webex sites and preferred sites of a user can be retrieved by [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    service: str = typer.Option(..., "--service", help="Service for schedule or sign-up pages."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if a user or application calling the API has the admin-level scopes. The admin may specify the email of a user on a site they manage and the API will return meeting participants of the meetings that are hosted by that user."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Tracking Codes.\n\n\b\nExample: wxcli meetings list-tracking-codes --service SERVICE"""
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Site URL', 'siteUrl'), ('Service', 'service'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_CREATE_REASSIGN_HOST = '{"hostEmail":"...","meetingIds":["..."]}'

@app.command("create-reassign-host", short_help="Reassign Meetings to a New Host.")
def create_reassign_host(
    host_email: str = typer.Option(None, "--host-email", help="(required) Email address of the new meeting host."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reassign Meetings to a New Host.\n\n\b\nExample: wxcli meetings create-reassign-host --json-body '{"hostEmail":"...","meetingIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_REASSIGN_HOST), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/reassignHost"
    if json_body:
        body = load_json_body(json_body)
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



_BODY_SKELETON_CREATE_END = '{"reason":"..."}'

@app.command("create-end", short_help="End a Meeting.")
def create_end(
    meeting_id: str = typer.Argument(help="from: wxcli meetings list-meetings"),
    reason: str = typer.Option(None, "--reason", help="The reason for ending the meeting. This field is optional."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """End a Meeting.\n\n\b\nExample: wxcli meetings create-end MEETING_ID\n\n\b\nExample --json-body: '{"reason":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_END), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/end"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if reason is not None:
            body["reason"] = reason
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


