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
    """Retrieve a person's Application Services Settings."""
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
    ring_devices_for_click_to_dial_calls_enabled: bool = typer.Option(None, "--ring-devices-for-click-to-dial-calls-enabled/--no-ring-devices-for-click-to-dial-calls-enabled", help=""),
    ring_devices_for_group_page_enabled: bool = typer.Option(None, "--ring-devices-for-group-page-enabled/--no-ring-devices-for-group-page-enabled", help=""),
    ring_devices_for_call_park_enabled: bool = typer.Option(None, "--ring-devices-for-call-park-enabled/--no-ring-devices-for-call-park-enabled", help=""),
    browser_client_enabled: bool = typer.Option(None, "--browser-client-enabled/--no-browser-client-enabled", help=""),
    desktop_client_enabled: bool = typer.Option(None, "--desktop-client-enabled/--no-desktop-client-enabled", help=""),
    tablet_client_enabled: bool = typer.Option(None, "--tablet-client-enabled/--no-tablet-client-enabled", help=""),
    mobile_client_enabled: bool = typer.Option(None, "--mobile-client-enabled/--no-mobile-client-enabled", help=""),
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
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    tone_enabled: bool = typer.Option(None, "--tone-enabled/--no-tone-enabled", help=""),
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
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
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
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    record: str = typer.Option(None, "--record", help=""),
    record_voicemail_enabled: bool = typer.Option(None, "--record-voicemail-enabled/--no-record-voicemail-enabled", help=""),
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
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
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



@app.command("show-caller-id")
def show_caller_id(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Caller ID Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callerId"
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



@app.command("update-caller-id")
def update_caller_id(
    person_id: str = typer.Argument(help="personId"),
    selected: str = typer.Option(None, "--selected", help="e.g. CUSTOM"),
    custom_number: str = typer.Option(None, "--custom-number", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    block_in_forward_calls_enabled: bool = typer.Option(None, "--block-in-forward-calls-enabled/--no-block-in-forward-calls-enabled", help=""),
    external_caller_id_name_policy: str = typer.Option(None, "--external-caller-id-name-policy", help="e.g. LOCATION"),
    custom_external_caller_id_name: str = typer.Option(None, "--custom-external-caller-id-name", help=""),
    additional_external_caller_id_direct_line_enabled: bool = typer.Option(None, "--additional-external-caller-id-direct-line-enabled/--no-additional-external-caller-id-direct-line-enabled", help=""),
    additional_external_caller_id_location_number_enabled: bool = typer.Option(None, "--additional-external-caller-id-location-number-enabled/--no-additional-external-caller-id-location-number-enabled", help=""),
    additional_external_caller_id_custom_number: str = typer.Option(None, "--additional-external-caller-id-custom-number", help=""),
    dial_by_first_name: str = typer.Option(None, "--dial-by-first-name", help=""),
    dial_by_last_name: str = typer.Option(None, "--dial-by-last-name", help=""),
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
    behavior_type: str = typer.Option(None, "--behavior-type", help="e.g. NATIVE_SIP_CALL_TO_UCM"),
    profile_id: str = typer.Option(None, "--profile-id", help=""),
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
    webex_go_override_enabled: bool = typer.Option(None, "--webex-go-override-enabled/--no-webex-go-override-enabled", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    ring_splash_enabled: bool = typer.Option(None, "--ring-splash-enabled/--no-ring-splash-enabled", help=""),
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
        if webex_go_override_enabled is not None:
            body["webexGoOverrideEnabled"] = webex_go_override_enabled
        if enabled is not None:
            body["enabled"] = enabled
        if ring_splash_enabled is not None:
            body["ringSplashEnabled"] = ring_splash_enabled
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
    type_param: str = typer.Option(None, "--type", help="e.g. EXECUTIVE"),
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
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
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



@app.command("show-monitoring")
def show_monitoring(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a person's Monitoring Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/monitoring"
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



@app.command("update-monitoring")
def update_monitoring(
    person_id: str = typer.Argument(help="personId"),
    enable_call_park_notification: bool = typer.Option(None, "--enable-call-park-notification/--no-enable-call-park-notification", help=""),
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
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help=""),
    external_transfer: str = typer.Option(None, "--external-transfer", help="e.g. ALLOW_ONLY_TRANSFERRED_EXTERNAL"),
    internal_calls_enabled: bool = typer.Option(None, "--internal-calls-enabled/--no-internal-calls-enabled", help=""),
    collect_calls_enabled: bool = typer.Option(None, "--collect-calls-enabled/--no-collect-calls-enabled", help=""),
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



@app.command("show-outgoing-permission")
def show_outgoing_permission(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a person's Outgoing Calling Permissions Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/outgoingPermission"
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



@app.command("update-outgoing-permission")
def update_outgoing_permission(
    person_id: str = typer.Argument(help="personId"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help=""),
    use_custom_permissions: bool = typer.Option(None, "--use-custom-permissions/--no-use-custom-permissions", help=""),
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



@app.command("list")
def cmd_list(
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
    items = result.get("numbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-privacy")
def show_privacy(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a person's Privacy Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/privacy"
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



@app.command("update-privacy")
def update_privacy(
    person_id: str = typer.Argument(help="personId"),
    aa_extension_dialing_enabled: bool = typer.Option(None, "--aa-extension-dialing-enabled/--no-aa-extension-dialing-enabled", help=""),
    aa_naming_dialing_enabled: bool = typer.Option(None, "--aa-naming-dialing-enabled/--no-aa-naming-dialing-enabled", help=""),
    enable_phone_status_directory_privacy: bool = typer.Option(None, "--enable-phone-status-directory-privacy/--no-enable-phone-status-directory-privacy", help=""),
    enable_phone_status_pickup_barge_in_privacy: bool = typer.Option(None, "--enable-phone-status-pickup-barge-in-privacy/--no-enable-phone-status-pickup-barge-in-privacy", help=""),
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



@app.command("show-push-to-talk")
def show_push_to_talk(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Push-to-Talk Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/pushToTalk"
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



@app.command("update-push-to-talk")
def update_push_to_talk(
    person_id: str = typer.Argument(help="personId"),
    allow_auto_answer: bool = typer.Option(None, "--allow-auto-answer/--no-allow-auto-answer", help=""),
    connection_type: str = typer.Option(None, "--connection-type", help="e.g. TWO_WAY"),
    access_type: str = typer.Option(None, "--access-type", help="e.g. ALLOW_MEMBERS"),
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
        if connection_type is not None:
            body["connectionType"] = connection_type
        if access_type is not None:
            body["accessType"] = access_type
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



@app.command("show-reception")
def show_reception(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Receptionist Client Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/reception"
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



@app.command("update-reception")
def update_reception(
    person_id: str = typer.Argument(help="personId"),
    reception_enabled: bool = typer.Option(None, "--reception-enabled/--no-reception-enabled", help=""),
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
    name: str = typer.Option(None, "--name", help=""),
    type_param: str = typer.Option(None, "--type", help=""),
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
        if type_param is not None:
            body["type"] = type_param
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



@app.command("update-schedules")
def update_schedules(
    person_id: str = typer.Argument(help="personId"),
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    new_name: str = typer.Option(None, "--new-name", help=""),
    name: str = typer.Option(None, "--name", help=""),
    type_param: str = typer.Option(None, "--type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if new_name is not None:
            body["newName"] = new_name
        if name is not None:
            body["name"] = name
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



@app.command("delete")
def delete(
    person_id: str = typer.Argument(help="personId"),
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Schedule."""
    if not force:
        typer.confirm(f"Delete {schedule_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {schedule_id}")



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
    new_name: str = typer.Option(None, "--new-name", help=""),
    name: str = typer.Option(None, "--name", help=""),
    start_date: str = typer.Option(None, "--start-date", help=""),
    end_date: str = typer.Option(None, "--end-date", help=""),
    start_time: str = typer.Option(None, "--start-time", help=""),
    end_time: str = typer.Option(None, "--end-time", help=""),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help=""),
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



@app.command("delete-events")
def delete_events(
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
    name: str = typer.Option(None, "--name", help=""),
    start_date: str = typer.Option(None, "--start-date", help=""),
    end_date: str = typer.Option(None, "--end-date", help=""),
    start_time: str = typer.Option(None, "--start-time", help=""),
    end_time: str = typer.Option(None, "--end-time", help=""),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help=""),
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
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
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


