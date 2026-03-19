import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling user-call-settings.")


@app.command("show")
def show(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a person's Application Services Settings New."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/applications"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update")
def update(
    person_id: str = typer.Argument(help="personId"),
    ring_devices_for_click_to_dial_calls_enabled: bool = typer.Option(None, "--ring-devices-for-click-to-dial-calls-enabled/--no-ring-devices-for-click-to-dial-calls-enabled", help="When `true`, indicates to ring devices for outbound Click to"),
    ring_devices_for_group_page_enabled: bool = typer.Option(None, "--ring-devices-for-group-page-enabled/--no-ring-devices-for-group-page-enabled", help="When `true`, indicates to ring devices for inbound Group Pag"),
    ring_devices_for_call_park_enabled: bool = typer.Option(None, "--ring-devices-for-call-park-enabled/--no-ring-devices-for-call-park-enabled", help="When `true`, indicates to ring devices for Call Park recalle"),
    browser_client_enabled: bool = typer.Option(None, "--browser-client-enabled/--no-browser-client-enabled", help="If `true`, the browser Webex Calling application is enabled"),
    desktop_client_enabled: bool = typer.Option(None, "--desktop-client-enabled/--no-desktop-client-enabled", help="If `true`, the desktop Webex Calling application is enabled"),
    tablet_client_enabled: bool = typer.Option(None, "--tablet-client-enabled/--no-tablet-client-enabled", help="If `true`, the tablet Webex Calling application is enabled f"),
    mobile_client_enabled: bool = typer.Option(None, "--mobile-client-enabled/--no-mobile-client-enabled", help="If `true`, the mobile Webex Calling application is enabled f"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a person's Application Services Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/applications"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if ring_devices_for_click_to_dial_calls_enabled is not None:
            body["ringDevicesForClickToDialCallsEnabled"] = ring_devices_for_click_to_dial_calls_enabled
        if ring_devices_for_group_page_enabled is not None:
            body["ringDevicesForGroupPageEnabled"] = ring_devices_for_group_page_enabled
        if ring_devices_for_call_park_enabled is not None:
            body["ringDevicesForCallParkEnabled"] = ring_devices_for_call_park_enabled
        if browser_client_enabled is not None:
            body["browserClientEnabled"] = browser_client_enabled
        if desktop_client_enabled is not None:
            body["desktopClientEnabled"] = desktop_client_enabled
        if tablet_client_enabled is not None:
            body["tabletClientEnabled"] = tablet_client_enabled
        if mobile_client_enabled is not None:
            body["mobileClientEnabled"] = mobile_client_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-barge-in")
def show_barge_in(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Barge In Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/bargeIn"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-barge-in")
def update_barge_in(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Set to enable or disable the Barge In feature."),
    tone_enabled: bool = typer.Option(None, "--tone-enabled/--no-tone-enabled", help="Set to enable or disable a stutter dial tone being played wh"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Barge In Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/bargeIn"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if tone_enabled is not None:
            body["toneEnabled"] = tone_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-call-forwarding")
def show_call_forwarding(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Forwarding Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callForwarding"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-call-forwarding")
def update_call_forwarding(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Forwarding Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callForwarding"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-intercept")
def show_intercept(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Intercept Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/intercept"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-intercept")
def update_intercept(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the intercept feature is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Intercept Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/intercept"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("configure-call-intercept")
def configure_call_intercept(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Intercept Greeting for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/intercept/actions/announcementUpload/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("show-call-recording")
def show_call_recording(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Recording Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callRecording"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-call-recording")
def update_call_recording(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if call recording is enabled."),
    record: str = typer.Option(None, "--record", help="Choices: Always, Never, Always with Pause/Resume, On Demand with User Initiated Start"),
    record_voicemail_enabled: bool = typer.Option(None, "--record-voicemail-enabled/--no-record-voicemail-enabled", help="When `true`, voicemail messages are also recorded."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Recording Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callRecording"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if record is not None:
            body["record"] = record
        if record_voicemail_enabled is not None:
            body["recordVoicemailEnabled"] = record_voicemail_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-call-waiting")
def show_call_waiting(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Waiting Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callWaiting"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-call-waiting")
def update_call_waiting(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Call Waiting feature is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Waiting Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callWaiting"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Caller ID Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callerId"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("types", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-caller-id-features")
def update_caller_id_features(
    person_id: str = typer.Argument(help="personId"),
    selected: str = typer.Option(None, "--selected", help="Choices: DIRECT_LINE, LOCATION_NUMBER, CUSTOM"),
    custom_number: str = typer.Option(None, "--custom-number", help="Custom number which will be shown if CUSTOM is selected. Thi"),
    first_name: str = typer.Option(None, "--first-name", help="Virtual line's Caller ID first name. The characters `%`,  `+"),
    last_name: str = typer.Option(None, "--last-name", help="Virtual line's Caller ID last name. The characters `%`,  `+`"),
    block_in_forward_calls_enabled: bool = typer.Option(None, "--block-in-forward-calls-enabled/--no-block-in-forward-calls-enabled", help="Block this virtual line's identity when receiving a call."),
    external_caller_id_name_policy: str = typer.Option(None, "--external-caller-id-name-policy", help="Choices: DIRECT_LINE, LOCATION, OTHER"),
    custom_external_caller_id_name: str = typer.Option(None, "--custom-external-caller-id-name", help="Custom external caller ID name which will be shown if extern"),
    additional_external_caller_id_direct_line_enabled: bool = typer.Option(None, "--additional-external-caller-id-direct-line-enabled/--no-additional-external-caller-id-direct-line-enabled", help="Set the virtual line's direct line number as additional exte"),
    additional_external_caller_id_location_number_enabled: bool = typer.Option(None, "--additional-external-caller-id-location-number-enabled/--no-additional-external-caller-id-location-number-enabled", help="Set the Location main number as additional external caller I"),
    additional_external_caller_id_custom_number: str = typer.Option(None, "--additional-external-caller-id-custom-number", help="To set a custom number as additional external caller ID for"),
    dial_by_first_name: str = typer.Option(None, "--dial-by-first-name", help="Sets or clears the first name to be used for dial-by-name fu"),
    dial_by_last_name: str = typer.Option(None, "--dial-by-last-name", help="Sets or clears the last name to be used for dial-by-name fun"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Caller ID Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callerId"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if custom_number is not None:
            body["customNumber"] = custom_number
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if block_in_forward_calls_enabled is not None:
            body["blockInForwardCallsEnabled"] = block_in_forward_calls_enabled
        if external_caller_id_name_policy is not None:
            body["externalCallerIdNamePolicy"] = external_caller_id_name_policy
        if custom_external_caller_id_name is not None:
            body["customExternalCallerIdName"] = custom_external_caller_id_name
        if additional_external_caller_id_direct_line_enabled is not None:
            body["additionalExternalCallerIdDirectLineEnabled"] = additional_external_caller_id_direct_line_enabled
        if additional_external_caller_id_location_number_enabled is not None:
            body["additionalExternalCallerIdLocationNumberEnabled"] = additional_external_caller_id_location_number_enabled
        if additional_external_caller_id_custom_number is not None:
            body["additionalExternalCallerIdCustomNumber"] = additional_external_caller_id_custom_number
        if dial_by_first_name is not None:
            body["dialByFirstName"] = dial_by_first_name
        if dial_by_last_name is not None:
            body["dialByLastName"] = dial_by_last_name
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-calling-behavior")
def show_calling_behavior(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Person's Calling Behavior."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callingBehavior"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-calling-behavior")
def update_calling_behavior(
    person_id: str = typer.Argument(help="personId"),
    behavior_type: str = typer.Option(None, "--behavior-type", help="Choices: NATIVE_WEBEX_TEAMS_CALLING, CALL_WITH_APP_REGISTERED_FOR_CISCOTEL, CALL_WITH_APP_REGISTERED_FOR_TEL, CALL_WITH_APP_REGISTERED_FOR_WEBEXCALLTEL, NATIVE_SIP_CALL_TO_UCM, null"),
    profile_id: str = typer.Option(None, "--profile-id", help="The UC Manager Profile ID. Specifying null results in the or"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure a person's Calling Behavior."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callingBehavior"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if behavior_type is not None:
            body["behaviorType"] = behavior_type
        if profile_id is not None:
            body["profileId"] = profile_id
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-do-not-disturb")
def show_do_not_disturb(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Do Not Disturb Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/doNotDisturb"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-do-not-disturb")
def update_do_not_disturb(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Do Not Disturb feature is enabled."),
    ring_splash_enabled: bool = typer.Option(None, "--ring-splash-enabled/--no-ring-splash-enabled", help="Enables a Ring Reminder to play a brief tone on your desktop"),
    webex_go_override_enabled: bool = typer.Option(None, "--webex-go-override-enabled/--no-webex-go-override-enabled", help="`true` if a mobile device will still ring even if Do Not Dis"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Do Not Disturb Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/doNotDisturb"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if ring_splash_enabled is not None:
            body["ringSplashEnabled"] = ring_splash_enabled
        if webex_go_override_enabled is not None:
            body["webexGoOverrideEnabled"] = webex_go_override_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-executive-assistant")
def show_executive_assistant(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Executive Assistant Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/executiveAssistant"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-executive-assistant")
def update_executive_assistant(
    person_id: str = typer.Argument(help="personId"),
    type_param: str = typer.Option(None, "--type", help="Choices: UNASSIGNED, EXECUTIVE, EXECUTIVE_ASSISTANT"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Executive Assistant Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/executiveAssistant"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-hoteling")
def show_hoteling(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Hoteling Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/hoteling"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-hoteling")
def update_hoteling(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="When `true`, allow this person to connect to a Hoteling host"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Hoteling Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/hoteling"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-monitoring")
def list_monitoring(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a person's Monitoring Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/monitoring"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("monitoredElements", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-monitoring")
def update_monitoring(
    person_id: str = typer.Argument(help="personId"),
    enable_call_park_notification: bool = typer.Option(None, "--enable-call-park-notification/--no-enable-call-park-notification", help="Enable or disable call park notification."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a person's Monitoring Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/monitoring"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enable_call_park_notification is not None:
            body["enableCallParkNotification"] = enable_call_park_notification
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-incoming-permission")
def show_incoming_permission(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Incoming Permission Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/incomingPermission"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-incoming-permission")
def update_incoming_permission(
    person_id: str = typer.Argument(help="personId"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help="When true, indicates that this virtual line uses the specifi"),
    external_transfer: str = typer.Option(None, "--external-transfer", help="Choices: ALLOW_ALL_EXTERNAL, ALLOW_ONLY_TRANSFERRED_EXTERNAL, BLOCK_ALL_EXTERNAL"),
    internal_calls_enabled: bool = typer.Option(None, "--internal-calls-enabled/--no-internal-calls-enabled", help="Internal calls are allowed to be received."),
    collect_calls_enabled: bool = typer.Option(None, "--collect-calls-enabled/--no-collect-calls-enabled", help="Collect calls are allowed to be received."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Incoming Permission Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/incomingPermission"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if use_custom_enabled is not None:
            body["useCustomEnabled"] = use_custom_enabled
        if external_transfer is not None:
            body["externalTransfer"] = external_transfer
        if internal_calls_enabled is not None:
            body["internalCallsEnabled"] = internal_calls_enabled
        if collect_calls_enabled is not None:
            body["collectCallsEnabled"] = collect_calls_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-outgoing-permission")
def list_outgoing_permission(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a person's Outgoing Calling Permissions Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/outgoingPermission"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("callingPermissions", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-outgoing-permission")
def update_outgoing_permission(
    person_id: str = typer.Argument(help="personId"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help="When true, indicates that this user uses the shared control"),
    use_custom_permissions: bool = typer.Option(None, "--use-custom-permissions/--no-use-custom-permissions", help="When true, indicates that this user uses the specified outgo"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a person's Outgoing Calling Permissions Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/outgoingPermission"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if use_custom_enabled is not None:
            body["useCustomEnabled"] = use_custom_enabled
        if use_custom_permissions is not None:
            body["useCustomPermissions"] = use_custom_permissions
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-numbers")
def list_numbers(
    person_id: str = typer.Argument(help="personId"),
    prefer_e164_format: str = typer.Option(None, "--prefer-e164-format", help="Return phone numbers in E.164 format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a List of Phone Numbers for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/numbers"
    params = {}
    if prefer_e164_format is not None:
        params["preferE164Format"] = prefer_e164_format
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("phoneNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Number', 'directNumber'), ('Extension', 'extension'), ('Primary', 'primary')], limit=limit)



@app.command("list-privacy")
def list_privacy(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a person's Privacy Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/privacy"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("monitoringAgents", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-privacy")
def update_privacy(
    person_id: str = typer.Argument(help="personId"),
    aa_extension_dialing_enabled: bool = typer.Option(None, "--aa-extension-dialing-enabled/--no-aa-extension-dialing-enabled", help="When `true` auto attendant extension dialing is enabled."),
    aa_naming_dialing_enabled: bool = typer.Option(None, "--aa-naming-dialing-enabled/--no-aa-naming-dialing-enabled", help="When `true` auto attendant dailing by first or last name is"),
    enable_phone_status_directory_privacy: bool = typer.Option(None, "--enable-phone-status-directory-privacy/--no-enable-phone-status-directory-privacy", help="When `true` phone status directory privacy is enabled."),
    enable_phone_status_pickup_barge_in_privacy: bool = typer.Option(None, "--enable-phone-status-pickup-barge-in-privacy/--no-enable-phone-status-pickup-barge-in-privacy", help="When `true` privacy is enforced for call pickup and barge-in"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure a person's Privacy Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/privacy"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if aa_extension_dialing_enabled is not None:
            body["aaExtensionDialingEnabled"] = aa_extension_dialing_enabled
        if aa_naming_dialing_enabled is not None:
            body["aaNamingDialingEnabled"] = aa_naming_dialing_enabled
        if enable_phone_status_directory_privacy is not None:
            body["enablePhoneStatusDirectoryPrivacy"] = enable_phone_status_directory_privacy
        if enable_phone_status_pickup_barge_in_privacy is not None:
            body["enablePhoneStatusPickupBargeInPrivacy"] = enable_phone_status_pickup_barge_in_privacy
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-push-to-talk")
def list_push_to_talk(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Push-to-Talk Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/pushToTalk"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("members", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-push-to-talk")
def update_push_to_talk(
    person_id: str = typer.Argument(help="personId"),
    allow_auto_answer: bool = typer.Option(None, "--allow-auto-answer/--no-allow-auto-answer", help="`true` if Push-to-Talk feature is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Push-to-Talk Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/pushToTalk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if allow_auto_answer is not None:
            body["allowAutoAnswer"] = allow_auto_answer
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-reception")
def list_reception(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Receptionist Client Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/reception"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("monitoredMembers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-reception")
def update_reception(
    person_id: str = typer.Argument(help="personId"),
    reception_enabled: bool = typer.Option(None, "--reception-enabled/--no-reception-enabled", help="`true` if the Receptionist Client feature is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Receptionist Client Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/reception"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if reception_enabled is not None:
            body["receptionEnabled"] = reception_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-schedules")
def list_schedules(
    person_id: str = typer.Argument(help="personId"),
    start: str = typer.Option(None, "--start", help="Specifies the offset from the first result that you want to"),
    max: str = typer.Option(None, "--max", help="Specifies the maximum number of records that you want to fet"),
    name: str = typer.Option(None, "--name", help="Specifies the case insensitive substring to be matched again"),
    type_param: str = typer.Option(None, "--type", help="Specifies the schedule event type to be matched on the given"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List of Schedules for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules"
    params = {}
    if start is not None:
        params["start"] = start
    if max is not None:
        params["max"] = max
    if name is not None:
        params["name"] = name
    if type_param is not None:
        params["type"] = type_param
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("schedules", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Level', 'level')], limit=limit)



@app.command("create")
def create(
    person_id: str = typer.Argument(help="personId"),
    name: str = typer.Option(..., "--name", help="Name for the schedule."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Schedule for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show-schedules")
def show_schedules(
    person_id: str = typer.Argument(help="personId"),
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Schedule Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("show-events")
def show_events(
    person_id: str = typer.Argument(help="personId"),
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch Event for a person's Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-events")
def update_events(
    person_id: str = typer.Argument(help="personId"),
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    new_name: str = typer.Option(None, "--new-name", help="New name for the event."),
    name: str = typer.Option(None, "--name", help="Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="Start date of the event, or first occurrence if repeating, i"),
    end_date: str = typer.Option(None, "--end-date", help="End date of the event, or first occurrence if repeating, in"),
    start_time: str = typer.Option(None, "--start-time", help="Start time of the event in the format of HH:MM (24 hours for"),
    end_time: str = typer.Option(None, "--end-time", help="End time of the event in the format of HH:MM (24 hours forma"),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="True if it is all-day event."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Event for a person's Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if new_name is not None:
            body["newName"] = new_name
        if name is not None:
            body["name"] = name
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if all_day_enabled is not None:
            body["allDayEnabled"] = all_day_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    person_id: str = typer.Argument(help="personId"),
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an Event for a person's Schedule."""
    if not force:
        typer.confirm(f"Delete {event_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {event_id}")



@app.command("create-events")
def create_events(
    person_id: str = typer.Argument(help="personId"),
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    name: str = typer.Option(..., "--name", help="Name for the event."),
    start_date: str = typer.Option(..., "--start-date", help="Start date of the event, or first occurrence if repeating, i"),
    end_date: str = typer.Option(..., "--end-date", help="End date of the event, or first occurrence if repeating, in"),
    start_time: str = typer.Option(..., "--start-time", help="Start time of the event in the format of `HH:MM` (24 hours f"),
    end_time: str = typer.Option(..., "--end-time", help="End time of the event in the format of `HH:MM` (24 hours for"),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="True if it is all-day event."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a New Event for Person's Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}/events"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if all_day_enabled is not None:
            body["allDayEnabled"] = all_day_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show-voicemail")
def show_voicemail(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Voicemail Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-voicemail")
def update_voicemail(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Voicemail is enabled or disabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Voicemail Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("configure-busy-voicemail")
def configure_busy_voicemail(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Busy Voicemail Greeting for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail/actions/uploadBusyGreeting/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("configure-no-answer")
def configure_no_answer(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure No Answer Voicemail Greeting for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail/actions/uploadNoAnswerGreeting/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("reset-voicemail-pin")
def reset_voicemail_pin(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reset Voicemail PIN."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail/actions/resetPin/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("list-move-location")
def list_move_location(
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of jobs. Default"),
    max: str = typer.Option(None, "--max", help="Limit the number of jobs returned to this maximum count. Def"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Move Users Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation"
    params = {}
    if start is not None:
        params["start"] = start
    if max is not None:
        params["max"] = max
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-move-location")
def create_move_location(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate or Initiate Move Users Job."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "response" in result:
        typer.echo(f"Created: {result['response']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show-move-location")
def show_move_location(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Move Users Job Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation/{job_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("pause-the-move")
def pause_the_move(
    job_id: str = typer.Argument(help="jobId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause the Move Users Job."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation/{job_id}/actions/pause/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("resume-the-move")
def resume_the_move(
    job_id: str = typer.Argument(help="jobId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume the Move Users Job."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation/{job_id}/actions/resume/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("list-errors")
def list_errors(
    job_id: str = typer.Argument(help="jobId"),
    start: str = typer.Option(None, "--start", help="Specifies the error offset from the first result that you wa"),
    max: str = typer.Option(None, "--max", help="Specifies the maximum number of records that you want to fet"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Move Users Job errors."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation/{job_id}/errors"
    params = {}
    if start is not None:
        params["start"] = start
    if max is not None:
        params["max"] = max
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-music-on-hold")
def show_music_on_hold(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Music On Hold Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/musicOnHold"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-music-on-hold")
def update_music_on_hold(
    person_id: str = typer.Argument(help="personId"),
    moh_enabled: bool = typer.Option(None, "--moh-enabled/--no-moh-enabled", help="Music on hold is enabled or disabled for the workspace."),
    greeting: str = typer.Option(None, "--greeting", help="Choices: DEFAULT, CUSTOM"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Music On Hold Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/musicOnHold"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if moh_enabled is not None:
            body["mohEnabled"] = moh_enabled
        if greeting is not None:
            body["greeting"] = greeting
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-access-codes")
def list_access_codes(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Access Codes for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/accessCodes"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("accessCodes", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-access-codes")
def create_access_codes(
    person_id: str = typer.Argument(help="personId"),
    code: str = typer.Option(..., "--code", help="An Access code."),
    description: str = typer.Option(..., "--description", help="The description of the access code."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Access Codes for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/accessCodes"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if code is not None:
            body["code"] = code
        if description is not None:
            body["description"] = description
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("update-access-codes")
def update_access_codes(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Access Codes for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/accessCodes"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-access-codes")
def delete_access_codes(
    person_id: str = typer.Argument(help="personId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Access Codes for a Person."""
    if not force:
        typer.confirm(f"Delete {person_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/accessCodes"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {person_id}")



@app.command("show-auto-transfer-numbers")
def show_auto_transfer_numbers(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Transfer Numbers for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/autoTransferNumbers"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-auto-transfer-numbers")
def update_auto_transfer_numbers(
    person_id: str = typer.Argument(help="personId"),
    use_custom_transfer_numbers: bool = typer.Option(None, "--use-custom-transfer-numbers/--no-use-custom-transfer-numbers", help="When `true`, use custom settings for the transfer numbers ca"),
    auto_transfer_number1: str = typer.Option(None, "--auto-transfer-number1", help="When calling a specific call type, this workspace will be au"),
    auto_transfer_number2: str = typer.Option(None, "--auto-transfer-number2", help="When calling a specific call type, this workspace will be au"),
    auto_transfer_number3: str = typer.Option(None, "--auto-transfer-number3", help="When calling a specific call type, this workspace will be au"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Transfer Numbers for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/autoTransferNumbers"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if use_custom_transfer_numbers is not None:
            body["useCustomTransferNumbers"] = use_custom_transfer_numbers
        if auto_transfer_number1 is not None:
            body["autoTransferNumber1"] = auto_transfer_number1
        if auto_transfer_number2 is not None:
            body["autoTransferNumber2"] = auto_transfer_number2
        if auto_transfer_number3 is not None:
            body["autoTransferNumber3"] = auto_transfer_number3
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-digit-patterns")
def list_digit_patterns(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Digit Patterns for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("digitPatterns", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-digit-patterns")
def create_digit_patterns(
    person_id: str = typer.Argument(help="personId"),
    name: str = typer.Option(..., "--name", help="A unique name for the digit pattern."),
    pattern: str = typer.Option(..., "--pattern", help="The digit pattern to be matched with the input number."),
    action: str = typer.Option(..., "--action", help="Choices: ALLOW, BLOCK, AUTH_CODE, TRANSFER_NUMBER_1, TRANSFER_NUMBER_2, TRANSFER_NUMBER_3"),
    transfer_enabled: bool = typer.Option(..., "--transfer-enabled", help="If `true`, allows transfer and forwarding for the call type."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Digit Patterns for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if pattern is not None:
            body["pattern"] = pattern
        if action is not None:
            body["action"] = action
        if transfer_enabled is not None:
            body["transferEnabled"] = transfer_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("update-digit-patterns-outgoing-permission")
def update_digit_patterns_outgoing_permission(
    person_id: str = typer.Argument(help="personId"),
    use_custom_digit_patterns: bool = typer.Option(None, "--use-custom-digit-patterns/--no-use-custom-digit-patterns", help="When `true`, use custom settings for the digit patterns cate"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify the Digit Pattern Category Control Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if use_custom_digit_patterns is not None:
            body["useCustomDigitPatterns"] = use_custom_digit_patterns
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-digit-patterns-outgoing-permission")
def delete_digit_patterns_outgoing_permission(
    person_id: str = typer.Argument(help="personId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete all Digit Patterns for a Person."""
    if not force:
        typer.confirm(f"Delete {person_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {person_id}")



@app.command("show-digit-patterns")
def show_digit_patterns(
    person_id: str = typer.Argument(help="personId"),
    digit_pattern_id: str = typer.Argument(help="digitPatternId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Digit Pattern Details for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-digit-patterns-outgoing-permission-1")
def update_digit_patterns_outgoing_permission_1(
    person_id: str = typer.Argument(help="personId"),
    digit_pattern_id: str = typer.Argument(help="digitPatternId"),
    name: str = typer.Option(None, "--name", help="A unique name for the digit pattern."),
    pattern: str = typer.Option(None, "--pattern", help="The digit pattern to be matched with the input number."),
    action: str = typer.Option(None, "--action", help="Choices: ALLOW, BLOCK, AUTH_CODE, TRANSFER_NUMBER_1, TRANSFER_NUMBER_2, TRANSFER_NUMBER_3"),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help="If `true`, allows transfer and forwarding for the call type."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Digit Pattern for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if pattern is not None:
            body["pattern"] = pattern
        if action is not None:
            body["action"] = action
        if transfer_enabled is not None:
            body["transferEnabled"] = transfer_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-digit-patterns-outgoing-permission-1")
def delete_digit_patterns_outgoing_permission_1(
    person_id: str = typer.Argument(help="personId"),
    digit_pattern_id: str = typer.Argument(help="digitPatternId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Digit Pattern for a Person."""
    if not force:
        typer.confirm(f"Delete {digit_pattern_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {digit_pattern_id}")



@app.command("update-numbers")
def update_numbers(
    person_id: str = typer.Argument(help="personId"),
    distinctive_ring_enabled: bool = typer.Option(None, "--distinctive-ring-enabled/--no-distinctive-ring-enabled", help="Enables a distinctive ring pattern for the person."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign or Unassign numbers to a person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/numbers"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if distinctive_ring_enabled is not None:
            body["distinctiveRingEnabled"] = distinctive_ring_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-preferred-answer-endpoint")
def list_preferred_answer_endpoint(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/preferredAnswerEndpoint"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("endpoints", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-preferred-answer-endpoint")
def update_preferred_answer_endpoint(
    person_id: str = typer.Argument(help="personId"),
    preferred_answer_endpoint_id: str = typer.Option(None, "--preferred-answer-endpoint-id", help="Person’s preferred answer endpoint."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/preferredAnswerEndpoint"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if preferred_answer_endpoint_id is not None:
            body["preferredAnswerEndpointId"] = preferred_answer_endpoint_id
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-available-members-applications")
def list_available_members_applications(
    person_id: str = typer.Argument(help="personId"),
    application_id: str = typer.Argument(help="applicationId"),
    max: str = typer.Option(None, "--max", help="Number of records per page."),
    start: str = typer.Option(None, "--start", help="Page number."),
    location: str = typer.Option(None, "--location", help="Location ID for the user."),
    name: str = typer.Option(None, "--name", help="Search for users with names that match the query."),
    number: str = typer.Option(None, "--number", help="Search for users with numbers that match the query."),
    order: str = typer.Option(None, "--order", help="Sort by first name (`fname`) or last name (`lname`)."),
    extension: str = typer.Option(None, "--extension", help="Search for users with extensions that match the query."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Shared-Line Appearance Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/{application_id}/availableMembers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if location is not None:
        params["location"] = location
    if name is not None:
        params["name"] = name
    if number is not None:
        params["number"] = number
    if order is not None:
        params["order"] = order
    if extension is not None:
        params["extension"] = extension
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("members", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-members-applications")
def list_members_applications(
    person_id: str = typer.Argument(help="personId"),
    application_id: str = typer.Argument(help="applicationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Shared-Line Appearance Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/{application_id}/members"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("members", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-members-applications")
def update_members_applications(
    person_id: str = typer.Argument(help="personId"),
    application_id: str = typer.Argument(help="applicationId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Put Shared-Line Appearance Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/{application_id}/members"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("update-passcode")
def update_passcode(
    person_id: str = typer.Argument(help="personId"),
    passcode: str = typer.Option(None, "--passcode", help="Voicemail access passcode. The minimum length of the passcod"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a person's voicemail passcode."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/voicemail/passcode"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if passcode is not None:
            body["passcode"] = passcode
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-summary")
def show_summary(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Message Summary."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/summary"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("list-voice-messages")
def list_voice_messages(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Messages."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("delete-voice-messages")
def delete_voice_messages(
    message_id: str = typer.Argument(help="messageId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Message."""
    if not force:
        typer.confirm(f"Delete {message_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/{message_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {message_id}")



@app.command("create-mark-as-read")
def create_mark_as_read(
    message_id: str = typer.Option(None, "--message-id", help="The voicemail message identifier of the message to mark as r"),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mark As Read."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/markAsRead"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if message_id is not None:
            body["messageId"] = message_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("create-mark-as-unread")
def create_mark_as_unread(
    message_id: str = typer.Option(None, "--message-id", help="The voicemail message identifier of the message to mark as u"),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mark As Unread."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/markAsUnread"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if message_id is not None:
            body["messageId"] = message_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("list-available-caller-ids")
def list_available_caller_ids(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Agent's List of Available Caller IDs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/agent/availableCallerIds"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("availableCallerIds", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-caller-id")
def show_caller_id(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Agent's Caller ID Information."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/agent/callerId"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-caller-id-agent")
def update_caller_id_agent(
    person_id: str = typer.Argument(help="personId"),
    selected_caller_id: str = typer.Option(None, "--selected-caller-id", help="The unique identifier of the call queue or hunt group to use"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Agent's Caller ID Information."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/agent/callerId"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected_caller_id is not None:
            body["selectedCallerId"] = selected_caller_id
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-call-bridge")
def show_call_bridge(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Bridge Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/callBridge"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-call-bridge")
def update_call_bridge(
    person_id: str = typer.Argument(help="personId"),
    warning_tone_enabled: bool = typer.Option(None, "--warning-tone-enabled/--no-warning-tone-enabled", help="Set to enable or disable a stutter dial tone being played to"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Bridge Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/callBridge"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if warning_tone_enabled is not None:
            body["warningToneEnabled"] = warning_tone_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-available-numbers-secondary")
def list_available_numbers_secondary(
    person_id: str = typer.Argument(help="personId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Secondary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/secondary/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("phoneNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-fax-message")
def list_available_numbers_fax_message(
    person_id: str = typer.Argument(help="personId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Fax Message Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/faxMessage/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("phoneNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-call-forwarding")
def list_available_numbers_call_forwarding(
    person_id: str = typer.Argument(help="personId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `exten"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Call Forward Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/callForwarding/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if owner_name is not None:
        params["ownerName"] = owner_name
    if extension is not None:
        params["extension"] = extension
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("phoneNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-primary")
def list_available_numbers_primary(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of phone numbers for this location within th"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    license_type: str = typer.Option(None, "--license-type", help="Choices: Webex Calling Professional, Webex Calling Standard"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Primary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/primary/availableNumbers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if license_type is not None:
        params["licenseType"] = license_type
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("phoneNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-emergency-callback-number")
def list_available_numbers_emergency_callback_number(
    person_id: str = typer.Argument(help="personId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person ECBN Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if owner_name is not None:
        params["ownerName"] = owner_name
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("phoneNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-call-intercept")
def list_available_numbers_call_intercept(
    person_id: str = typer.Argument(help="personId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `exten"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Call Intercept Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/callIntercept/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if owner_name is not None:
        params["ownerName"] = owner_name
    if extension is not None:
        params["extension"] = extension
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("phoneNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-ms-teams")
def list_ms_teams(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a Person's MS Teams Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/settings/msTeams"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("settings", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-ms-teams")
def update_ms_teams(
    person_id: str = typer.Argument(help="personId"),
    setting_name: str = typer.Option(None, "--setting-name", help="Choices: HIDE_WEBEX_APP"),
    value: bool = typer.Option(None, "--value/--no-value", help="The boolean value to update the `HIDE_WEBEX_APP` setting, ei"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure a Person's MS Teams Setting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/settings/msTeams"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if setting_name is not None:
            body["settingName"] = setting_name
        if value is not None:
            body["value"] = value
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-personal-assistant")
def show_personal_assistant(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Personal Assistant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/personalAssistant"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-personal-assistant")
def update_personal_assistant(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Toggles feature."),
    presence: str = typer.Option(None, "--presence", help="Person's availability.  * `NONE` - User is available.  * `BU (use --help for choices)"),
    until_date_time: str = typer.Option(None, "--until-date-time", help="The date until which the personal assistant is active."),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help="If `true`, allows transfer and forwarding for the call type."),
    transfer_number: str = typer.Option(None, "--transfer-number", help="Number to transfer to."),
    alerting: str = typer.Option(None, "--alerting", help="Choices: ALERT_ME_FIRST, PLAY_RING_REMINDER, NONE"),
    alert_me_first_number_of_rings: str = typer.Option(None, "--alert-me-first-number-of-rings", help="Number of rings for alert type: ALERT_ME_FIRST; available ra"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Personal Assistant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/personalAssistant"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if presence is not None:
            body["presence"] = presence
        if until_date_time is not None:
            body["untilDateTime"] = until_date_time
        if transfer_enabled is not None:
            body["transferEnabled"] = transfer_enabled
        if transfer_number is not None:
            body["transferNumber"] = transfer_number
        if alerting is not None:
            body["alerting"] = alerting
        if alert_me_first_number_of_rings is not None:
            body["alertMeFirstNumberOfRings"] = alert_me_first_number_of_rings
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-available-features")
def list_available_features(
    person_id: str = typer.Argument(help="personId"),
    name: str = typer.Option(None, "--name", help="List features whose `name` contains this string."),
    phone_number: str = typer.Option(None, "--phone-number", help="List features whose phoneNumber contains this matching strin"),
    extension: str = typer.Option(None, "--extension", help="List features whose `extension` contains this matching strin"),
    max: str = typer.Option(None, "--max", help="Maximum number of features to return in a single page."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    order: str = typer.Option(None, "--order", help="Sort the list of features based on `name`, `phoneNumber`, or"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve the List of Available Features."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/modeManagement/availableFeatures"
    params = {}
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("features", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-mode-management")
def list_mode_management(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve the List of Features Assigned to a User for Mode Management."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/modeManagement/features"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("features", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-mode-management")
def update_mode_management(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign a List of Features to a User for Mode Management."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/modeManagement/features"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-selective-accept")
def list_selective_accept(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the User’s Selective Call Accept Criteria List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("criteria", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-selective-accept")
def update_selective_accept(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="indicates whether selective accept is enabled or not."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User’s Selective Call Accept Criteria."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create-criteria-selective-accept")
def create_criteria_selective_accept(
    person_id: str = typer.Argument(help="personId"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    accept_enabled: bool = typer.Option(..., "--accept-enabled", help="Boolean flag indicating if selective call accept is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Criteria to the User’s Selective Call Accept Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if accept_enabled is not None:
            body["acceptEnabled"] = accept_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show-criteria-selective-accept")
def show_criteria_selective_accept(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Criteria for the User’s Selective Call Accept Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-criteria-selective-accept")
def update_criteria_selective_accept(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    accept_enabled: bool = typer.Option(None, "--accept-enabled/--no-accept-enabled", help="Boolean flag to enable/disable the selective accept criteria"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Criteria From the User’s Selective Call Accept Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if accept_enabled is not None:
            body["acceptEnabled"] = accept_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-criteria-selective-accept")
def delete_criteria_selective_accept(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Criteria From the User’s Selective Call Accept service."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {id}")



@app.command("list-selective-reject")
def list_selective_reject(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the User’s Selective Call Rejection Criteria Listing."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("criteria", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-selective-reject")
def update_selective_reject(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="if `true`, selective reject is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User’s Selective Call Rejection Criteria List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create-criteria-selective-reject")
def create_criteria_selective_reject(
    person_id: str = typer.Argument(help="personId"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    reject_enabled: bool = typer.Option(..., "--reject-enabled", help="Boolean flag to enable/disable rejection."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Criteria to the User’s Selective Call Rejection Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if reject_enabled is not None:
            body["rejectEnabled"] = reject_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show-criteria-selective-reject")
def show_criteria_selective_reject(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Criteria for the User’s Selective Call Rejection Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-criteria-selective-reject")
def update_criteria_selective_reject(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    reject_enabled: bool = typer.Option(None, "--reject-enabled/--no-reject-enabled", help="Boolean flag to enable/disable rejection."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Criteria for the User’s Selective Call Rejection Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if reject_enabled is not None:
            body["rejectEnabled"] = reject_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-criteria-selective-reject")
def delete_criteria_selective_reject(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Criteria From the User’s Selective Call Rejection Service."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {id}")



@app.command("list-selective-forward")
def list_selective_forward(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the User’s Selective Call Forwarding."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("criteria", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-selective-forward")
def update_selective_forward(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Selective Forward feature is enabled."),
    default_phone_number_to_forward: str = typer.Option(None, "--default-phone-number-to-forward", help="Enter the phone number to forward calls to during this sched"),
    ring_reminder_enabled: bool = typer.Option(None, "--ring-reminder-enabled/--no-ring-reminder-enabled", help="When `true`, enables a ring reminder for such calls."),
    destination_voicemail_enabled: bool = typer.Option(None, "--destination-voicemail-enabled/--no-destination-voicemail-enabled", help="Enables forwarding for all calls to voicemail. This option i"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User’s Selective Call Forwarding Criteria List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if default_phone_number_to_forward is not None:
            body["defaultPhoneNumberToForward"] = default_phone_number_to_forward
        if ring_reminder_enabled is not None:
            body["ringReminderEnabled"] = ring_reminder_enabled
        if destination_voicemail_enabled is not None:
            body["destinationVoicemailEnabled"] = destination_voicemail_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create-criteria-selective-forward")
def create_criteria_selective_forward(
    person_id: str = typer.Argument(help="personId"),
    forward_to_phone_number: str = typer.Option(..., "--forward-to-phone-number", help="Number to which calls needs to be forwarded."),
    send_to_voicemail_enabled: bool = typer.Option(..., "--send-to-voicemail-enabled", help="Boolean flag to enable/disable sending calls to voicemail."),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Calls From custom numbers, private number enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Calls From custom numbers, unavailable number enabled."),
    forward_enabled: bool = typer.Option(None, "--forward-enabled/--no-forward-enabled", help="Boolean flag to enable/disable selective call forward."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Criteria to the User’s Selective Call Forwarding Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
        if send_to_voicemail_enabled is not None:
            body["sendToVoicemailEnabled"] = send_to_voicemail_enabled
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if forward_enabled is not None:
            body["forwardEnabled"] = forward_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show-criteria-selective-forward")
def show_criteria_selective_forward(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Criteria for the User’s Selective Call Forwarding Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-criteria-selective-forward")
def update_criteria_selective_forward(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="Number to which calls needs to be forwarded."),
    send_to_voicemail_enabled: bool = typer.Option(None, "--send-to-voicemail-enabled/--no-send-to-voicemail-enabled", help="Boolean flag to enable/disable sending calls to voicemail."),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    forward_enabled: bool = typer.Option(None, "--forward-enabled/--no-forward-enabled", help="Boolean flag to enable/disable selective call forwarding."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Criteria for the User’s Selective Call Forwarding Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
        if send_to_voicemail_enabled is not None:
            body["sendToVoicemailEnabled"] = send_to_voicemail_enabled
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if forward_enabled is not None:
            body["forwardEnabled"] = forward_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-criteria-selective-forward")
def delete_criteria_selective_forward(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Criteria From the User’s Selective Call Forwarding Service."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {id}")



@app.command("list-available-members-applications-1")
def list_available_members_applications_1(
    person_id: str = typer.Argument(help="personId"),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    order: str = typer.Option(None, "--order", help="Order the Route Lists according to number, ascending or desc"),
    location: str = typer.Option(None, "--location", help="Location ID for the user."),
    name: str = typer.Option(None, "--name", help="Search for users with names that match the query."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for users with numbers that match the query."),
    extension: str = typer.Option(None, "--extension", help="Search for users with extensions that match the query."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Shared-Line Appearance Members New."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/availableMembers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if order is not None:
        params["order"] = order
    if location is not None:
        params["location"] = location
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("members", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-count")
def show_count(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Count of Shared-Line Appearance Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/availableMembers/count"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("list-members-applications-1")
def list_members_applications_1(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Shared-Line Appearance Members New."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/members"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("members", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-members-applications-1")
def update_members_applications_1(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Put Shared-Line Appearance Members New."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/members"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-call-captions")
def show_call_captions(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the user call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/callCaptions"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-call-captions")
def update_call_captions(
    person_id: str = typer.Argument(help="personId"),
    user_closed_captions_enabled: bool = typer.Option(None, "--user-closed-captions-enabled/--no-user-closed-captions-enabled", help="Enable or disable user-level closed captions."),
    user_transcripts_enabled: bool = typer.Option(None, "--user-transcripts-enabled/--no-user-transcripts-enabled", help="Enable or disable user-level transcripts."),
    use_location_settings_enabled: bool = typer.Option(None, "--use-location-settings-enabled/--no-use-location-settings-enabled", help="If `useLocationSettingsEnabled` is `true`, location settings"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the user call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/callCaptions"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if user_closed_captions_enabled is not None:
            body["userClosedCaptionsEnabled"] = user_closed_captions_enabled
        if user_transcripts_enabled is not None:
            body["userTranscriptsEnabled"] = user_transcripts_enabled
        if use_location_settings_enabled is not None:
            body["useLocationSettingsEnabled"] = use_location_settings_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-call-filtering")
def list_call_filtering(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Call Filtering Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("criteria", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-call-filtering")
def update_call_filtering(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Set to `true` to enable executive call filtering or `false`"),
    filter_type: str = typer.Option(None, "--filter-type", help="Choices: CUSTOM_CALL_FILTERS, ALL_CALLS, ALL_INTERNAL_CALLS, ALL_EXTERNAL_CALLS"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Call Filtering Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if filter_type is not None:
            body["filterType"] = filter_type
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-criteria-call-filtering")
def show_criteria_call_filtering(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Call Filtering Criteria Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-criteria-call-filtering")
def update_criteria_call_filtering(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule associated with this criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: holidays, businessHours"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Set to enable or disable the criteria for anonymous callers."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Set to enable or disable the criteria for unavailable caller"),
    filter_enabled: bool = typer.Option(None, "--filter-enabled/--no-filter-enabled", help="Controls the action when this criteria matches a call. When"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Call Filtering Criteria Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if filter_enabled is not None:
            body["filterEnabled"] = filter_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-criteria-call-filtering")
def delete_criteria_call_filtering(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Person Executive Call Filtering Criteria."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {id}")



@app.command("create-criteria-call-filtering")
def create_criteria_call_filtering(
    person_id: str = typer.Argument(help="personId"),
    filter_name: str = typer.Option(..., "--filter-name", help="Name of the criteria."),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule associated with this criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: holidays, businessHours"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(..., "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Set to enable or disable the criteria for anonymous callers."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Set to enable or disable the criteria for unavailable caller"),
    filter_enabled: bool = typer.Option(..., "--filter-enabled", help="Controls the action when this criteria matches a call. When"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add Person Executive Call Filtering Criteria."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if filter_name is not None:
            body["filterName"] = filter_name
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if filter_enabled is not None:
            body["filterEnabled"] = filter_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show-alert")
def show_alert(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Alert Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/alert"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-alert")
def update_alert(
    person_id: str = typer.Argument(help="personId"),
    alerting_mode: str = typer.Option(None, "--alerting-mode", help="Choices: SEQUENTIAL, SIMULTANEOUS"),
    next_assistant_number_of_rings: str = typer.Option(None, "--next-assistant-number-of-rings", help="Number of rings before alerting the next assistant when `ale"),
    rollover_enabled: bool = typer.Option(None, "--rollover-enabled/--no-rollover-enabled", help="Controls whether the rollover timer (`rolloverWaitTimeInSecs"),
    rollover_action: str = typer.Option(None, "--rollover-action", help="Choices: VOICE_MESSAGING, NO_ANSWER_PROCESSING, FORWARD"),
    rollover_forward_to_phone_number: str = typer.Option(None, "--rollover-forward-to-phone-number", help="Phone number to forward calls to when rollover action is set"),
    rollover_wait_time_in_secs: str = typer.Option(None, "--rollover-wait-time-in-secs", help="Time in seconds to wait before applying the rollover action"),
    clid_name_mode: str = typer.Option(None, "--clid-name-mode", help="Choices: EXECUTIVE_ORIGINATOR, ORIGINATOR_EXECUTIVE, EXECUTIVE, ORIGINATOR, CUSTOM"),
    custom_clid_name: str = typer.Option(None, "--custom-clid-name", help="Custom caller ID name to display when `clidNameMode` is set"),
    custom_clid_name_in_unicode: str = typer.Option(None, "--custom-clid-name-in-unicode", help="Unicode Custom caller ID name to display when `clidNameMode`"),
    clid_phone_number_mode: str = typer.Option(None, "--clid-phone-number-mode", help="Choices: EXECUTIVE, ORIGINATOR, CUSTOM"),
    custom_clid_phone_number: str = typer.Option(None, "--custom-clid-phone-number", help="Custom caller ID phone number to display on assistant's phon"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Alert Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/alert"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if alerting_mode is not None:
            body["alertingMode"] = alerting_mode
        if next_assistant_number_of_rings is not None:
            body["nextAssistantNumberOfRings"] = next_assistant_number_of_rings
        if rollover_enabled is not None:
            body["rolloverEnabled"] = rollover_enabled
        if rollover_action is not None:
            body["rolloverAction"] = rollover_action
        if rollover_forward_to_phone_number is not None:
            body["rolloverForwardToPhoneNumber"] = rollover_forward_to_phone_number
        if rollover_wait_time_in_secs is not None:
            body["rolloverWaitTimeInSecs"] = rollover_wait_time_in_secs
        if clid_name_mode is not None:
            body["clidNameMode"] = clid_name_mode
        if custom_clid_name is not None:
            body["customCLIDName"] = custom_clid_name
        if custom_clid_name_in_unicode is not None:
            body["customCLIDNameInUnicode"] = custom_clid_name_in_unicode
        if clid_phone_number_mode is not None:
            body["clidPhoneNumberMode"] = clid_phone_number_mode
        if custom_clid_phone_number is not None:
            body["customCLIDPhoneNumber"] = custom_clid_phone_number
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-assigned-assistants")
def list_assigned_assistants(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Assigned Assistants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/assignedAssistants"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("assistants", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-assigned-assistants")
def update_assigned_assistants(
    person_id: str = typer.Argument(help="personId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Assigned Assistants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/assignedAssistants"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-available-assistants")
def list_available_assistants(
    person_id: str = typer.Argument(help="personId"),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Only return people with the matching name (person's first an"),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return people with the matching phone number or extensi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Available Assistants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/availableAssistants"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("assistants", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-assistant")
def list_assistant(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Assistant Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/assistant"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("executives", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-assistant")
def update_assistant(
    person_id: str = typer.Argument(help="personId"),
    forward_filtered_calls_enabled: bool = typer.Option(None, "--forward-filtered-calls-enabled/--no-forward-filtered-calls-enabled", help="If `true`, filtered calls to assistant are forwarded to the"),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="Phone number to forward the filtered calls to. Mandatory if"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Assistant Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/assistant"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if forward_filtered_calls_enabled is not None:
            body["forwardFilteredCallsEnabled"] = forward_filtered_calls_enabled
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-screening")
def show_screening(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Screening Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/screening"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-screening")
def update_screening(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Set to enable or disable executive screening."),
    alert_type: str = typer.Option(None, "--alert-type", help="Choices: SILENT, RING_SPLASH"),
    alert_anywhere_location_enabled: bool = typer.Option(None, "--alert-anywhere-location-enabled/--no-alert-anywhere-location-enabled", help="Indicates if alerts are enabled for Single Number Reach loca"),
    alert_mobility_location_enabled: bool = typer.Option(None, "--alert-mobility-location-enabled/--no-alert-mobility-location-enabled", help="Indicates if alerts are enabled for Webex Go locations."),
    alert_shared_call_appearance_location_enabled: bool = typer.Option(None, "--alert-shared-call-appearance-location-enabled/--no-alert-shared-call-appearance-location-enabled", help="Indicates if alerts are enabled for Shared Call Appearance l"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Screening Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/screening"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if alert_type is not None:
            body["alertType"] = alert_type
        if alert_anywhere_location_enabled is not None:
            body["alertAnywhereLocationEnabled"] = alert_anywhere_location_enabled
        if alert_mobility_location_enabled is not None:
            body["alertMobilityLocationEnabled"] = alert_mobility_location_enabled
        if alert_shared_call_appearance_location_enabled is not None:
            body["alertSharedCallAppearanceLocationEnabled"] = alert_shared_call_appearance_location_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")


