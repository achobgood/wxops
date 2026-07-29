import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-preferences.")


@app.command("list", short_help="Get Meeting Preference Details.")
def cmd_list(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the required [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will return..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Preference Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
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
    items = result.get("sites", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Site URL', 'siteUrl'), ('Default', 'default')], limit=limit)



@app.command("list-personal-meeting-room", short_help="Get Personal Meeting Room Options.")
def list_personal_meeting_room(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will return details..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Personal Meeting Room Options."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/personalMeetingRoom"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
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
    items = result.get("coHosts", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Display Name', 'displayName'), ('Email', 'email')], limit=limit)



_BODY_SKELETON_UPDATE = '{"topic":"...","hostPin":"...","enabledAutoLock":true,"autoLockMinutes":0,"enabledNotifyHost":true,"supportCoHost":true,"coHosts":[{"email":"...","displayName":"..."}],"supportAnyoneAsCoHost":true,"allowFirstUserToBeCoHost":true,"allowAuthenticatedDevices":true}'

@app.command("update", short_help="Update Personal Meeting Room Options.")
def update(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will update Personal..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    topic: str = typer.Option(None, "--topic", help="Personal Meeting Room topic to be updated."),
    host_pin: str = typer.Option(None, "--host-pin", help="Updated PIN for joining the room as host. The host PIN must be digits of a predefined length, e.g. 4 digits. It cannot contain sequential digits, such as 1234 or 4321, or repeated digits of the predefined length, such as 1111. The predefined length for host PIN can be viewed in user's `My Personal..."),
    enabled_auto_lock: bool = typer.Option(None, "--enabled-auto-lock/--no-enabled-auto-lock", help="Update for option to automatically lock the Personal Room a number of minutes after a meeting starts. When a room is locked, invitees cannot enter until the owner admits them. The period after which the meeting is locked is defined by `autoLockMinutes`."),
    auto_lock_minutes: str = typer.Option(None, "--auto-lock-minutes", help="Updated number of minutes after which the Personal Room is locked if `enabledAutoLock` is enabled. Valid options are 0, 5, 10, 15 and 20."),
    enabled_notify_host: bool = typer.Option(None, "--enabled-notify-host/--no-enabled-notify-host", help="Update for flag to enable notifying the owner of a Personal Room when someone enters the Personal Room lobby while the owner is not in the room."),
    support_co_host: bool = typer.Option(None, "--support-co-host/--no-support-co-host", help="Update for flag allowing other invitees to host a meetingCoHost in the Personal Room without the owner."),
    support_anyone_as_co_host: bool = typer.Option(None, "--support-anyone-as-co-host/--no-support-anyone-as-co-host", help="Whether or not to allow any attendee with a host account on the target site to become a cohost when joining the Personal Room. The target site is user's preferred site."),
    allow_first_user_to_be_co_host: bool = typer.Option(None, "--allow-first-user-to-be-co-host/--no-allow-first-user-to-be-co-host", help="Whether or not to allow the first attendee with a host account on the target site to become a cohost when joining the Personal Room. The target site is user's preferred site."),
    allow_authenticated_devices: bool = typer.Option(None, "--allow-authenticated-devices/--no-allow-authenticated-devices", help="Whether or not to allow authenticated video devices in the user's organization to start or join the meeting without a prompt."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Personal Meeting Room Options.\n\n\b\nExample: wxcli meeting-preferences update --json-body '{"topic":"...","hostPin":"...","enabledAutoLock":true,"autoLockMinutes":0,"enabledNotifyHost":true,"supportCoHost":true,"coHosts":[{"email":"...","displayName":"..."}]}'\n\n\b\nExample --json-body: '{"topic":"...","hostPin":"...","enabledAutoLock":true,"autoLockMinutes":0,"enabledNotifyHost":true,"supportCoHost":true,"coHosts":[{"email":"...","displayName":"..."}],"supportAnyoneAsCoHost":true,"allowFirstUserToBeCoHost":true,"allowAuthenticatedDevices":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/personalMeetingRoom"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if topic is not None:
            body["topic"] = topic
        if host_pin is not None:
            body["hostPin"] = host_pin
        if enabled_auto_lock is not None:
            body["enabledAutoLock"] = enabled_auto_lock
        if auto_lock_minutes is not None:
            body["autoLockMinutes"] = auto_lock_minutes
        if enabled_notify_host is not None:
            body["enabledNotifyHost"] = enabled_notify_host
        if support_co_host is not None:
            body["supportCoHost"] = support_co_host
        if support_anyone_as_co_host is not None:
            body["supportAnyoneAsCoHost"] = support_anyone_as_co_host
        if allow_first_user_to_be_co_host is not None:
            body["allowFirstUserToBeCoHost"] = allow_first_user_to_be_co_host
        if allow_authenticated_devices is not None:
            body["allowAuthenticatedDevices"] = allow_authenticated_devices
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



@app.command("show", short_help="Get Audio Options.")
def show(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will return details..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Audio Options."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/audio"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_AUDIO = '{"defaultAudioType":"webexAudio","otherTeleconferenceDescription":"...","enabledGlobalCallIn":true,"enabledTollFree":true,"enabledAutoConnection":true,"officeNumber":{"countryCode":"...","number":"...","enabledCallInAuthentication":true,"enabledCallMe":true},"mobileNumber":{"countryCode":"...","number":"...","enabledCallInAuthentication":true,"enabledCallMe":true},"audioPin":"..."}'

@app.command("update-audio", short_help="Update Audio Options.")
def update_audio(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will update audio..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    default_audio_type: str = typer.Option(None, "--default-audio-type", help="Choices: webexAudio, voipOnly, otherTeleconferenceService, none"),
    other_teleconference_description: str = typer.Option(None, "--other-teleconference-description", help="Phone number and other information for the teleconference provider to be used, along with instructions for invitees. This attribute can be modified with the with the [Update Audio Options](/docs/api/v1/meeting-preferences/update-audio-options) API."),
    enabled_global_call_in: bool = typer.Option(None, "--enabled-global-call-in/--no-enabled-global-call-in", help="Flag to enable/disable global call ins. ***Note***: If the site does not support global call-ins, you cannot set this option. This attribute can be modified with the with the [Update Audio Options](/docs/api/v1/meeting-preferences/update-audio-options) API."),
    enabled_toll_free: bool = typer.Option(None, "--enabled-toll-free/--no-enabled-toll-free", help="Flag to enable/disable call-ins from toll-free numbers. ***Note***: If the site does not support calls from toll-free numbers, you cannot set this option. This attribute can be modified with the with the [Update Audio Options](/docs/api/v1/meeting-preferences/update-audio-options) API."),
    enabled_auto_connection: bool = typer.Option(None, "--enabled-auto-connection/--no-enabled-auto-connection", help="Flag to enable/disable automatically connecting to audio using a computer. The meeting host can enable/disable this option. When this option is set to `true`, the user is automatically connected to audio via a computer when they start or join a Webex Meetings meeting on a desktop. This attribute..."),
    audio_pin: str = typer.Option(None, "--audio-pin", help="PIN to provide a secondary level of authentication for calls where the host is using the phone and may need to invite additional invitees. It must be exactly 4 digits. It cannot contain sequential digits, such as 1234 or 4321, or repeat a digit 4 times, such as 1111. This attribute can be modified..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Audio Options.\n\n\b\nExample: wxcli meeting-preferences update-audio --json-body '{"defaultAudioType":"webexAudio","otherTeleconferenceDescription":"...","enabledGlobalCallIn":true,"enabledTollFree":true,"enabledAutoConnection":true,"officeNumber":{"countryCode":"...","number":"...","enabledCallInAuthentication":true,"enabledCallMe":true},"mobileNumber":{"countryCode":"...","number":"...","enabledCallInAuthentication":true,"enabledCallMe":true}}'\n\n\b\nExample --json-body: '{"defaultAudioType":"webexAudio","otherTeleconferenceDescription":"...","enabledGlobalCallIn":true,"enabledTollFree":true,"enabledAutoConnection":true,"officeNumber":{"countryCode":"...","number":"...","enabledCallInAuthentication":true,"enabledCallMe":true},"mobileNumber":{"countryCode":"...","number":"...","enabledCallInAuthentication":true,"enabledCallMe":true},"audioPin":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_AUDIO), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/audio"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if default_audio_type is not None:
            body["defaultAudioType"] = default_audio_type
        if other_teleconference_description is not None:
            body["otherTeleconferenceDescription"] = other_teleconference_description
        if enabled_global_call_in is not None:
            body["enabledGlobalCallIn"] = enabled_global_call_in
        if enabled_toll_free is not None:
            body["enabledTollFree"] = enabled_toll_free
        if enabled_auto_connection is not None:
            body["enabledAutoConnection"] = enabled_auto_connection
        if audio_pin is not None:
            body["audioPin"] = audio_pin
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



@app.command("list-video", short_help="Get Video Options.")
def list_video(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will return details..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Video Options."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/video"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
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
    items = result.get("videoDevices", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Device Name', 'deviceName'), ('Device Address', 'deviceAddress'), ('Is Default', 'isDefault')], limit=limit)



_BODY_SKELETON_UPDATE_VIDEO = '{"videoDevices":[{"deviceName":"...","deviceAddress":"...","isDefault":true}]}'

@app.command("update-video", short_help="Update Video Options.")
def update_video(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will update video..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Video Options.\n\n\b\nExample: wxcli meeting-preferences update-video --json-body '{"videoDevices":[{"deviceName":"...","deviceAddress":"...","isDefault":true}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VIDEO), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/video"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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



@app.command("list-scheduling-options", short_help="Get Scheduling Options.")
def list_scheduling_options(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will return details..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Scheduling Options."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/schedulingOptions"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
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
    items = result.get("delegateEmails", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_UPDATE_SCHEDULING_OPTIONS = '{"enabledJoinBeforeHost":true,"joinBeforeHostMinutes":0,"enabledAutoShareRecording":true,"enabledWebexAssistantByDefault":true,"delegateEmails":["..."]}'

@app.command("update-scheduling-options", short_help="Update Scheduling Options.")
def update_scheduling_options(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will update..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    enabled_join_before_host: bool = typer.Option(None, "--enabled-join-before-host/--no-enabled-join-before-host", help="Flag to enable/disable ***Join Before Host***. The period during which invitees can join before the start time is defined by `autoLockMinutes`. This attribute can be modified with the [Update Scheduling Options](/docs/api/v1/meeting-preferences/update-scheduling-options) API. ***Note***: This..."),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help="Number of minutes before the start time that an invitee can join a meeting if `enabledJoinBeforeHost` is true. Valid options are 0, 5, 10 and 15. This attribute can be modified with the [Update Scheduling Options](/docs/api/v1/meeting-preferences/update-scheduling-options) API."),
    enabled_auto_share_recording: bool = typer.Option(None, "--enabled-auto-share-recording/--no-enabled-auto-share-recording", help="Flag to enable/disable the automatic sharing of the meeting recording with invitees when it is available. This attribute can be modified with the [Update Scheduling Options](/docs/api/v1/meeting-preferences/update-scheduling-options) API."),
    enabled_webex_assistant_by_default: bool = typer.Option(None, "--enabled-webex-assistant-by-default/--no-enabled-webex-assistant-by-default", help="Flag to automatically enable Webex Assistant whenever you start a meeting. This attribute can be modified with the [Update Scheduling Options](/docs/api/v1/meeting-preferences/update-scheduling-options) API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Scheduling Options.\n\n\b\nExample: wxcli meeting-preferences update-scheduling-options --enabled-join-before-host --join-before-host-minutes JOIN_BEFORE_HOST_MINUTES --enabled-auto-share-recording\n\n\b\nExample --json-body: '{"enabledJoinBeforeHost":true,"joinBeforeHostMinutes":0,"enabledAutoShareRecording":true,"enabledWebexAssistantByDefault":true,"delegateEmails":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SCHEDULING_OPTIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/schedulingOptions"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled_join_before_host is not None:
            body["enabledJoinBeforeHost"] = enabled_join_before_host
        if join_before_host_minutes is not None:
            body["joinBeforeHostMinutes"] = join_before_host_minutes
        if enabled_auto_share_recording is not None:
            body["enabledAutoShareRecording"] = enabled_auto_share_recording
        if enabled_webex_assistant_by_default is not None:
            body["enabledWebexAssistantByDefault"] = enabled_webex_assistant_by_default
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



_BODY_SKELETON_CREATE = '{"emails":["..."]}'

@app.command("create", short_help="Insert Delegate Emails.")
def create(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will update..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Insert Delegate Emails.\n\n\b\nExample --json-body: '{"emails":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/schedulingOptions/delegateEmails/insert"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
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



_BODY_SKELETON_DELETE_DELEGATE_EMAILS = '{"emails":["..."]}'

@app.command("create-delete", hidden=True)
@app.command("delete-delegate-emails", short_help="Delete Delegate Emails.")
def delete_delegate_emails(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will update..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `siteUrl` is not specified, the query will use the default site of the user. For admin use, if `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call. In the case where the user..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Delegate Emails.\n\n\b\nExample --json-body: '{"emails":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE_DELEGATE_EMAILS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/schedulingOptions/delegateEmails/delete"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
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
        typer.echo("Deleted.")
    else:
        emit(result, output=output, fields=fields)



@app.command("list-sites", short_help="Get Site List.")
def list_sites(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user and the API will return the list of Webex sites for..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. If `siteUrl` is not specified, the query will use the default site for the admin's authorization token used to make the call."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Site List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/sites"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
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
    items = result.get("sites", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Site URL', 'siteUrl'), ('Default', 'default')], limit=limit)



_BODY_SKELETON_UPDATE_SITES = '{"siteUrl":"..."}'

@app.command("update-sites", short_help="Update Default Site.")
def update_sites(
    default_site: str = typer.Option(..., "--default-site", help="Whether or not to change user's default site. ***Note***: `defaultSite` should be set to true for the user's single default site"),
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if the user or application calling the API has the [admin-level scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will update default..."),
    site_url: str = typer.Option(None, "--site-url", help="Access URL for the site."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Default Site.\n\n\b\nExample: wxcli meeting-preferences update-sites --default-site DEFAULT_SITE --site-url SITE_URL\n\n\b\nExample --json-body: '{"siteUrl":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SITES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/sites"
    params = {}
    if default_site is not None:
        params["defaultSite"] = default_site
    if user_email is not None:
        params["userEmail"] = user_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
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



_BODY_SKELETON_CREATE_REFRESH_ID = '{"siteUrl":"...","personalMeetingRoomIds":[{"email":"...","personId":"...","systemGenerated":true,"personalMeetingRoomId":"..."}]}'

@app.command("create-refresh-id", short_help="Batch Refresh Personal Meeting Room ID.")
def create_refresh_id(
    site_url: str = typer.Option(None, "--site-url", help="(required) Site URL to refresh the personal room IDs."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Refresh Personal Meeting Room ID.\n\n\b\nExample: wxcli meeting-preferences create-refresh-id --site-url SITE_URL\n\n\b\nExample --json-body: '{"siteUrl":"...","personalMeetingRoomIds":[{"email":"...","personId":"...","systemGenerated":true,"personalMeetingRoomId":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_REFRESH_ID), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetingPreferences/personalMeetingRoom/refreshId"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
        _missing = [f for f in ['siteUrl'] if f not in body or body[f] is None]
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


