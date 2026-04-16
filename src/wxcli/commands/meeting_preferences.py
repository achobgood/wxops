import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-preferences.")


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
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    enabled_toll_free: str = typer.Option(None, "--enabled-toll-free", help=""),
    enabled_auto_connection: str = typer.Option(None, "--enabled-auto-connection", help=""),
    audio_pin: str = typer.Option(None, "--audio-pin", help=""),
    default_audio_type: str = typer.Option(None, "--default-audio-type", help=""),
    other_teleconference_description: str = typer.Option(None, "--other-teleconference-description", help=""),
    enabled_global_call_in: str = typer.Option(None, "--enabled-global-call-in", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Audio Options\n\nExample --json-body:\n  '{"enabledTollFree":"...","enabledAutoConnection":"...","officeNumber":{"enabledCallInAuthentication":"...","enabledCallMe":"...","countryCode":"...","number":"..."},"audioPin":"...","mobileNumber":{"enabledCallInAuthentication":"...","enabledCallMe":"...","countryCode":"...","number":"..."},"defaultAudioType":"..."}'."""
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
        if enabled_toll_free is not None:
            body["enabledTollFree"] = enabled_toll_free
        if enabled_auto_connection is not None:
            body["enabledAutoConnection"] = enabled_auto_connection
        if audio_pin is not None:
            body["audioPin"] = audio_pin
        if default_audio_type is not None:
            body["defaultAudioType"] = default_audio_type
        if other_teleconference_description is not None:
            body["otherTeleconferenceDescription"] = other_teleconference_description
        if enabled_global_call_in is not None:
            body["enabledGlobalCallIn"] = enabled_global_call_in
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



@app.command("list")
def cmd_list(
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
    items = result.get("delegateEmails", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-scheduling-options")
def update_scheduling_options(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    enabled_webex_assistant_by_default: str = typer.Option(None, "--enabled-webex-assistant-by-default", help=""),
    enabled_join_before_host: str = typer.Option(None, "--enabled-join-before-host", help=""),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help=""),
    enabled_auto_share_recording: str = typer.Option(None, "--enabled-auto-share-recording", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Scheduling Options\n\nExample --json-body:\n  '{"enabledWebexAssistantByDefault":"...","delegateEmails":["..."],"enabledJoinBeforeHost":"...","joinBeforeHostMinutes":"...","enabledAutoShareRecording":"..."}'."""
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
        if enabled_webex_assistant_by_default is not None:
            body["enabledWebexAssistantByDefault"] = enabled_webex_assistant_by_default
        if enabled_join_before_host is not None:
            body["enabledJoinBeforeHost"] = enabled_join_before_host
        if join_before_host_minutes is not None:
            body["joinBeforeHostMinutes"] = join_before_host_minutes
        if enabled_auto_share_recording is not None:
            body["enabledAutoShareRecording"] = enabled_auto_share_recording
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



@app.command("create")
def create(
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
    items = result.get("sites", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-sites")
def update_sites(
    default_site: str = typer.Option(None, "--default-site", help="Whether or not to change user's default site. ***Note***: `d"),
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help=""),
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



@app.command("create-refresh-id")
def create_refresh_id(
    site_url: str = typer.Option(None, "--site-url", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Refresh Personal Meeting Room ID\n\nExample --json-body:\n  '{"siteUrl":"...","personalMeetingRoomIds":[{"personalMeetingRoomId":"...","email":"...","systemGenerated":"...","personId":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetingPreferences/personalMeetingRoom/refreshId"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
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



@app.command("list-meeting-preferences")
def list_meeting_preferences(
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
    items = result.get("sites", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-insert")
def create_insert(
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
    items = result.get("coHosts", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-personal-meeting-room")
def update_personal_meeting_room(
    user_email: str = typer.Option(None, "--user-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site to query. For individual use, if `site"),
    support_anyone_as_co_host: str = typer.Option(None, "--support-anyone-as-co-host", help=""),
    allow_first_user_to_be_co_host: str = typer.Option(None, "--allow-first-user-to-be-co-host", help=""),
    host_pin: str = typer.Option(None, "--host-pin", help=""),
    enabled_auto_lock: str = typer.Option(None, "--enabled-auto-lock", help=""),
    enabled_notify_host: str = typer.Option(None, "--enabled-notify-host", help=""),
    support_co_host: str = typer.Option(None, "--support-co-host", help=""),
    allow_authenticated_devices: str = typer.Option(None, "--allow-authenticated-devices", help=""),
    topic: str = typer.Option(None, "--topic", help=""),
    auto_lock_minutes: str = typer.Option(None, "--auto-lock-minutes", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Personal Meeting Room Options\n\nExample --json-body:\n  '{"supportAnyoneAsCoHost":"...","allowFirstUserToBeCoHost":"...","hostPin":"...","coHosts":[{"displayName":"...","email":"..."}],"enabledAutoLock":"...","enabledNotifyHost":"..."}'."""
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
        if support_anyone_as_co_host is not None:
            body["supportAnyoneAsCoHost"] = support_anyone_as_co_host
        if allow_first_user_to_be_co_host is not None:
            body["allowFirstUserToBeCoHost"] = allow_first_user_to_be_co_host
        if host_pin is not None:
            body["hostPin"] = host_pin
        if enabled_auto_lock is not None:
            body["enabledAutoLock"] = enabled_auto_lock
        if enabled_notify_host is not None:
            body["enabledNotifyHost"] = enabled_notify_host
        if support_co_host is not None:
            body["supportCoHost"] = support_co_host
        if allow_authenticated_devices is not None:
            body["allowAuthenticatedDevices"] = allow_authenticated_devices
        if topic is not None:
            body["topic"] = topic
        if auto_lock_minutes is not None:
            body["autoLockMinutes"] = auto_lock_minutes
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


