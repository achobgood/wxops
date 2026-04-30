import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-preferences.")


@app.command("list")
def cmd_list(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("sites", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-personal-meeting-room")
def list_personal_meeting_room(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("coHosts", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update")
def update(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    topic: str = typer.Option(None, "--topic", help="Personal Meeting Room topic to be updated."),
    host_pin: str = typer.Option(None, "--host-pin", help="Updated PIN for joining the room as host. The host PIN must"),
    enabled_auto_lock: bool = typer.Option(None, "--enabled-auto-lock/--no-enabled-auto-lock", help="Update for option to automatically lock the Personal Room a"),
    auto_lock_minutes: str = typer.Option(None, "--auto-lock-minutes", help="Updated number of minutes after which the Personal Room is l"),
    enabled_notify_host: bool = typer.Option(None, "--enabled-notify-host/--no-enabled-notify-host", help="Update for flag to enable notifying the owner of a Personal"),
    support_co_host: bool = typer.Option(None, "--support-co-host/--no-support-co-host", help="Update for flag allowing other invitees to host a meetingCoH"),
    support_anyone_as_co_host: bool = typer.Option(None, "--support-anyone-as-co-host/--no-support-anyone-as-co-host", help="Whether or not to allow any attendee with a host account on"),
    allow_first_user_to_be_co_host: bool = typer.Option(None, "--allow-first-user-to-be-co-host/--no-allow-first-user-to-be-co-host", help="Whether or not to allow the first attendee with a host accou"),
    allow_authenticated_devices: bool = typer.Option(None, "--allow-authenticated-devices/--no-allow-authenticated-devices", help="Whether or not to allow authenticated video devices in the u"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Personal Meeting Room Options\n\nExample --json-body:\n  '{"topic":"...","hostPin":"...","enabledAutoLock":true,"autoLockMinutes":0,"enabledNotifyHost":true,"supportCoHost":true,"coHosts":[{"email":"...","displayName":"..."}],"supportAnyoneAsCoHost":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/personalMeetingRoom"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("show")
def show(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-audio")
def update_audio(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    default_audio_type: str = typer.Option(None, "--default-audio-type", help="Choices: webexAudio, voipOnly, otherTeleconferenceService, none"),
    other_teleconference_description: str = typer.Option(None, "--other-teleconference-description", help="Phone number and other information for the teleconference pr"),
    enabled_global_call_in: bool = typer.Option(None, "--enabled-global-call-in/--no-enabled-global-call-in", help="Flag to enable/disable global call ins. ***Note***: If the s"),
    enabled_toll_free: bool = typer.Option(None, "--enabled-toll-free/--no-enabled-toll-free", help="Flag to enable/disable call-ins from toll-free numbers.  ***"),
    enabled_auto_connection: bool = typer.Option(None, "--enabled-auto-connection/--no-enabled-auto-connection", help="Flag to enable/disable automatically connecting to audio usi"),
    audio_pin: str = typer.Option(None, "--audio-pin", help="PIN to provide a secondary level of authentication for calls"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Audio Options\n\nExample --json-body:\n  '{"defaultAudioType":"webexAudio","otherTeleconferenceDescription":"...","enabledGlobalCallIn":true,"enabledTollFree":true,"enabledAutoConnection":true,"officeNumber":{"countryCode":"...","number":"...","enabledCallInAuthentication":true,"enabledCallMe":true},"mobileNumber":{"countryCode":"...","number":"...","enabledCallInAuthentication":true,"enabledCallMe":true},"audioPin":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/audio"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("list-video")
def list_video(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("videoDevices", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-video")
def update_video(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Video Options\n\nExample --json-body:\n  '{"videoDevices":[{"deviceName":"...","deviceAddress":"...","isDefault":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/video"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-scheduling-options")
def list_scheduling_options(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("delegateEmails", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-scheduling-options")
def update_scheduling_options(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    enabled_join_before_host: bool = typer.Option(None, "--enabled-join-before-host/--no-enabled-join-before-host", help="Flag to enable/disable ***Join Before Host***. The period du"),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help="Number of minutes before the start time that an invitee can"),
    enabled_auto_share_recording: bool = typer.Option(None, "--enabled-auto-share-recording/--no-enabled-auto-share-recording", help="Flag to enable/disable the automatic sharing of the meeting"),
    enabled_webex_assistant_by_default: bool = typer.Option(None, "--enabled-webex-assistant-by-default/--no-enabled-webex-assistant-by-default", help="Flag to automatically enable Webex Assistant whenever you st"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Scheduling Options\n\nExample --json-body:\n  '{"enabledJoinBeforeHost":true,"joinBeforeHostMinutes":0,"enabledAutoShareRecording":true,"enabledWebexAssistantByDefault":true,"delegateEmails":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/schedulingOptions"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("create")
def create(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Insert Delegate Emails\n\nExample --json-body:\n  '{"emails":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/schedulingOptions/delegateEmails/insert"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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



@app.command("create-delete")
def create_delete(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Delegate Emails\n\nExample --json-body:\n  '{"emails":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/schedulingOptions/delegateEmails/delete"
    params = {}
    if user_email is not None:
        params["userEmail"] = user_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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



@app.command("list-sites")
def list_sites(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. If `siteUrl` is not specifie"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("sites", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-sites")
def update_sites(
    default_site: str = typer.Option(..., "--default-site", help="Whether or not to change user's default site. ***Note***: `d"),
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="Access URL for the site."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Default Site."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingPreferences/sites"
    params = {}
    if default_site is not None:
        params["defaultSite"] = default_site
    if user_email is not None:
        params["userEmail"] = user_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-refresh-id")
def create_refresh_id(
    site_url: str = typer.Option(None, "--site-url", help="(required) Site URL to refresh the personal room IDs."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Refresh Personal Meeting Room ID\n\nExample --json-body:\n  '{"siteUrl":"...","personalMeetingRoomIds":[{"email":"...","personId":"...","systemGenerated":"...","personalMeetingRoomId":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetingPreferences/personalMeetingRoom/refreshId"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


