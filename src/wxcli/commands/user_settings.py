import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling user-settings.")


@app.command("show", short_help="Retrieve a person's Application Services Settings New.")
def show(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a person's Application Services Settings New.\n\n\b\nExample: wxcli user-settings show PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/applications"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"ringDevicesForClickToDialCallsEnabled":true,"ringDevicesForGroupPageEnabled":true,"ringDevicesForCallParkEnabled":true,"browserClientEnabled":true,"desktopClientEnabled":true,"tabletClientEnabled":true,"mobileClientEnabled":true}'

@app.command("update", short_help="Modify a person's Application Services Settings.")
def update(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    ring_devices_for_click_to_dial_calls_enabled: bool = typer.Option(None, "--ring-devices-for-click-to-dial-calls-enabled/--no-ring-devices-for-click-to-dial-calls-enabled", help="When `true`, indicates to ring devices for outbound Click to Dial calls."),
    ring_devices_for_group_page_enabled: bool = typer.Option(None, "--ring-devices-for-group-page-enabled/--no-ring-devices-for-group-page-enabled", help="When `true`, indicates to ring devices for inbound Group Pages."),
    ring_devices_for_call_park_enabled: bool = typer.Option(None, "--ring-devices-for-call-park-enabled/--no-ring-devices-for-call-park-enabled", help="When `true`, indicates to ring devices for Call Park recalled."),
    browser_client_enabled: bool = typer.Option(None, "--browser-client-enabled/--no-browser-client-enabled", help="If `true`, the browser Webex Calling application is enabled for use."),
    desktop_client_enabled: bool = typer.Option(None, "--desktop-client-enabled/--no-desktop-client-enabled", help="If `true`, the desktop Webex Calling application is enabled for use."),
    tablet_client_enabled: bool = typer.Option(None, "--tablet-client-enabled/--no-tablet-client-enabled", help="If `true`, the tablet Webex Calling application is enabled for use."),
    mobile_client_enabled: bool = typer.Option(None, "--mobile-client-enabled/--no-mobile-client-enabled", help="If `true`, the mobile Webex Calling application is enabled for use."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a person's Application Services Settings.\n\n\b\nExample: wxcli user-settings update PERSON_ID\n\n\b\nExample --json-body: '{"ringDevicesForClickToDialCallsEnabled":true,"ringDevicesForGroupPageEnabled":true,"ringDevicesForCallParkEnabled":true,"browserClientEnabled":true,"desktopClientEnabled":true,"tabletClientEnabled":true,"mobileClientEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/applications"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-barge-in", short_help="Read Barge In Settings for a Person.")
def show_barge_in(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Barge In Settings for a Person.\n\n\b\nExample: wxcli user-settings show-barge-in PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/bargeIn"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_BARGE_IN = '{"enabled":true,"toneEnabled":true}'

@app.command("update-barge-in", short_help="Configure Barge In Settings for a Person.")
def update_barge_in(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Set to enable or disable the Barge In feature."),
    tone_enabled: bool = typer.Option(None, "--tone-enabled/--no-tone-enabled", help="Set to enable or disable a stutter dial tone being played when a virtual line is barging in on the active call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Barge In Settings for a Person.\n\n\b\nExample: wxcli user-settings update-barge-in PERSON_ID\n\n\b\nExample --json-body: '{"enabled":true,"toneEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_BARGE_IN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/bargeIn"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if tone_enabled is not None:
            body["toneEnabled"] = tone_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-call-forwarding", short_help="Read Forwarding Settings for a Person.")
def show_call_forwarding(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Forwarding Settings for a Person.\n\n\b\nExample: wxcli user-settings show-call-forwarding PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callForwarding"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_FORWARDING = '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"busy":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"noAnswer":{"enabled":true,"destination":"...","numberOfRings":0,"destinationVoicemailEnabled":true}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'

@app.command("update-call-forwarding", short_help="Configure Call Forwarding Settings for a Person.")
def update_call_forwarding(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Forwarding Settings for a Person.\n\n\b\nExample: wxcli user-settings update-call-forwarding PERSON_ID\n\n\b\nExample --json-body: '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"busy":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"noAnswer":{"enabled":true,"destination":"...","numberOfRings":0,"destinationVoicemailEnabled":true}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_FORWARDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callForwarding"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-intercept", short_help="Read Call Intercept Settings for a Person.")
def show_intercept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Intercept Settings for a Person.\n\n\b\nExample: wxcli user-settings show-intercept PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/intercept"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_INTERCEPT = '{"enabled":true,"incoming":{"type":"INTERCEPT_ALL","voicemailEnabled":true,"announcements":{"greeting":"CUSTOM","newNumber":{"enabled":true,"destination":"..."},"zeroTransfer":{"enabled":true,"destination":"..."}}},"outgoing":{"type":"INTERCEPT_ALL","transferEnabled":true,"destination":"..."}}'

@app.command("update-intercept", short_help="Configure Call Intercept Settings for a Person.")
def update_intercept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the intercept feature is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Intercept Settings for a Person.\n\n\b\nExample: wxcli user-settings update-intercept PERSON_ID\n\n\b\nExample --json-body: '{"enabled":true,"incoming":{"type":"INTERCEPT_ALL","voicemailEnabled":true,"announcements":{"greeting":"CUSTOM","newNumber":{"enabled":true,"destination":"..."},"zeroTransfer":{"enabled":true,"destination":"..."}}},"outgoing":{"type":"INTERCEPT_ALL","transferEnabled":true,"destination":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_INTERCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/intercept"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("configure-call-intercept", short_help="Configure Call Intercept Greeting for a Person.")
def configure_call_intercept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Intercept Greeting for a Person.\n\n\b\nExample: wxcli user-settings configure-call-intercept PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/intercept/actions/announcementUpload/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    emit(result, output=output, fields=fields)



@app.command("show-call-recording", short_help="Read Call Recording Settings for a Person.")
def show_call_recording(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Recording Settings for a Person.\n\n\b\nExample: wxcli user-settings show-call-recording PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callRecording"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_RECORDING = '{"enabled":true,"record":"Always","recordVoicemailEnabled":true,"notification":{"type":"Beep","enabled":true},"repeat":{"interval":0,"enabled":true},"startStopAnnouncement":{"internalCallsEnabled":true,"pstnCallsEnabled":true}}'

@app.command("update-call-recording", short_help="Configure Call Recording Settings for a Person.")
def update_call_recording(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if call recording is enabled."),
    record: str = typer.Option(None, "--record", help="Choices: Always, Never, Always with Pause/Resume, On Demand with User Initiated Start"),
    record_voicemail_enabled: bool = typer.Option(None, "--record-voicemail-enabled/--no-record-voicemail-enabled", help="When `true`, voicemail messages are also recorded."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Recording Settings for a Person.\n\n\b\nExample: wxcli user-settings update-call-recording PERSON_ID\n\n\b\nExample --json-body: '{"enabled":true,"record":"Always","recordVoicemailEnabled":true,"notification":{"type":"Beep","enabled":true},"repeat":{"interval":0,"enabled":true},"startStopAnnouncement":{"internalCallsEnabled":true,"pstnCallsEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_RECORDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callRecording"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if record is not None:
            body["record"] = record
        if record_voicemail_enabled is not None:
            body["recordVoicemailEnabled"] = record_voicemail_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-call-waiting", short_help="Read Call Waiting Settings for a Person.")
def show_call_waiting(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Waiting Settings for a Person.\n\n\b\nExample: wxcli user-settings show-call-waiting PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callWaiting"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_WAITING = '{"enabled":true}'

@app.command("update-call-waiting", short_help="Configure Call Waiting Settings for a Person.")
def update_call_waiting(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Call Waiting feature is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Waiting Settings for a Person.\n\n\b\nExample: wxcli user-settings update-call-waiting PERSON_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_WAITING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callWaiting"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list", short_help="Read Caller ID Settings for a Person.")
def cmd_list(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Caller ID Settings for a Person.\n\n\b\nExample: wxcli user-settings list PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callerId"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("types", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_UPDATE_CALLER_ID_FEATURES = '{"selected":"DIRECT_LINE","customNumber":"...","firstName":"...","lastName":"...","blockInForwardCallsEnabled":true,"externalCallerIdNamePolicy":"DIRECT_LINE","customExternalCallerIdName":"...","additionalExternalCallerIdDirectLineEnabled":true,"additionalExternalCallerIdLocationNumberEnabled":true,"additionalExternalCallerIdCustomNumber":"...","directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByFirstName":"...","dialByLastName":"..."}'

@app.command("update-caller-id-features", short_help="Configure Caller ID Settings for a Person.")
def update_caller_id_features(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    selected: str = typer.Option(None, "--selected", help="Choices: DIRECT_LINE, LOCATION_NUMBER, CUSTOM"),
    custom_number: str = typer.Option(None, "--custom-number", help="Custom number which will be shown if CUSTOM is selected. This value must be a number from the virtual line's location or from another location with the same country, PSTN provider, and zone (only applicable for India locations) as the virtual line's location."),
    first_name: str = typer.Option(None, "--first-name", help="Virtual line's Caller ID first name. The characters `%`, `+`, ``, `\"` and Unicode characters are not allowed. This field has been deprecated. Please use `directLineCallerIdName` and `dialByFirstName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Virtual line's Caller ID last name. The characters `%`, `+`, ``, `\"` and Unicode characters are not allowed. This field has been deprecated. Please use `directLineCallerIdName` and `dialByLastName` instead."),
    block_in_forward_calls_enabled: bool = typer.Option(None, "--block-in-forward-calls-enabled/--no-block-in-forward-calls-enabled", help="Block this virtual line's identity when receiving a call."),
    external_caller_id_name_policy: str = typer.Option(None, "--external-caller-id-name-policy", help="Choices: DIRECT_LINE, LOCATION, OTHER"),
    custom_external_caller_id_name: str = typer.Option(None, "--custom-external-caller-id-name", help="Custom external caller ID name which will be shown if external caller ID name policy is `OTHER`."),
    additional_external_caller_id_direct_line_enabled: bool = typer.Option(None, "--additional-external-caller-id-direct-line-enabled/--no-additional-external-caller-id-direct-line-enabled", help="Set the virtual line's direct line number as additional external caller ID."),
    additional_external_caller_id_location_number_enabled: bool = typer.Option(None, "--additional-external-caller-id-location-number-enabled/--no-additional-external-caller-id-location-number-enabled", help="Set the Location main number as additional external caller ID for the virtual line."),
    additional_external_caller_id_custom_number: str = typer.Option(None, "--additional-external-caller-id-custom-number", help="To set a custom number as additional external caller ID for the virtual line. This value must be a number from the virtual line's location or from another location with the same country, PSTN provider, and zone (only applicable for India locations) as the virtual line's location."),
    dial_by_first_name: str = typer.Option(None, "--dial-by-first-name", help="Sets or clears the first name to be used for dial-by-name functions. To clear the `dialByFirstName`, the attribute must be set to null or empty string. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    dial_by_last_name: str = typer.Option(None, "--dial-by-last-name", help="Sets or clears the last name to be used for dial-by-name functions. To clear the `dialByLastName`, the attribute must be set to null or empty string. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Caller ID Settings for a Person.\n\n\b\nExample: wxcli user-settings update-caller-id-features PERSON_ID --selected DIRECT_LINE\n\n\b\nExample --json-body: '{"selected":"DIRECT_LINE","customNumber":"...","firstName":"...","lastName":"...","blockInForwardCallsEnabled":true,"externalCallerIdNamePolicy":"DIRECT_LINE","customExternalCallerIdName":"...","additionalExternalCallerIdDirectLineEnabled":true,"additionalExternalCallerIdLocationNumberEnabled":true,"additionalExternalCallerIdCustomNumber":"...","directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByFirstName":"...","dialByLastName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALLER_ID_FEATURES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callerId"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-calling-behavior", short_help="Read Person's Calling Behavior.")
def show_calling_behavior(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Person's Calling Behavior.\n\n\b\nExample: wxcli user-settings show-calling-behavior PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callingBehavior"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALLING_BEHAVIOR = '{"behaviorType":"NATIVE_WEBEX_TEAMS_CALLING","profileId":"..."}'

@app.command("update-calling-behavior", short_help="Configure a person's Calling Behavior.")
def update_calling_behavior(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    behavior_type: str = typer.Option(None, "--behavior-type", help="Choices: NATIVE_WEBEX_TEAMS_CALLING, CALL_WITH_APP_REGISTERED_FOR_CISCOTEL, CALL_WITH_APP_REGISTERED_FOR_TEL, CALL_WITH_APP_REGISTERED_FOR_WEBEXCALLTEL, NATIVE_SIP_CALL_TO_UCM"),
    profile_id: str = typer.Option(None, "--profile-id", help="The UC Manager Profile ID. Specifying null results in the organizational default being applied. In addition, when `behaviorType` is set to `CALL_WITH_APP_REGISTERED_FOR_CISCOTEL`, then the profile ID value will be cleared irrespective of any value being passed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure a person's Calling Behavior.\n\n\b\nExample: wxcli user-settings update-calling-behavior PERSON_ID\n\n\b\nExample --json-body: '{"behaviorType":"NATIVE_WEBEX_TEAMS_CALLING","profileId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALLING_BEHAVIOR), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/callingBehavior"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if behavior_type is not None:
            body["behaviorType"] = behavior_type
        if profile_id is not None:
            body["profileId"] = profile_id
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-do-not-disturb", short_help="Read Do Not Disturb Settings for a Person.")
def show_do_not_disturb(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Do Not Disturb Settings for a Person.\n\n\b\nExample: wxcli user-settings show-do-not-disturb PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/doNotDisturb"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_DO_NOT_DISTURB = '{"webexGoOverrideEnabled":true,"enabled":true,"ringSplashEnabled":true}'

@app.command("update-do-not-disturb", short_help="Configure Do Not Disturb Settings for a Person.")
def update_do_not_disturb(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Do Not Disturb feature is enabled."),
    ring_splash_enabled: bool = typer.Option(None, "--ring-splash-enabled/--no-ring-splash-enabled", help="Enables a Ring Reminder to play a brief tone on your desktop phone when you receive incoming calls."),
    webex_go_override_enabled: bool = typer.Option(None, "--webex-go-override-enabled/--no-webex-go-override-enabled", help="`true` if a mobile device will still ring even if Do Not Disturb is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Do Not Disturb Settings for a Person.\n\n\b\nExample: wxcli user-settings update-do-not-disturb PERSON_ID --webex-go-override-enabled\n\n\b\nExample --json-body: '{"webexGoOverrideEnabled":true,"enabled":true,"ringSplashEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DO_NOT_DISTURB), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/doNotDisturb"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if ring_splash_enabled is not None:
            body["ringSplashEnabled"] = ring_splash_enabled
        if webex_go_override_enabled is not None:
            body["webexGoOverrideEnabled"] = webex_go_override_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-executive-assistant", short_help="Retrieve Executive Assistant Settings for a Person.")
def show_executive_assistant(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Executive Assistant Settings for a Person.\n\n\b\nExample: wxcli user-settings show-executive-assistant PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/executiveAssistant"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_EXECUTIVE_ASSISTANT = '{"type":"UNASSIGNED"}'

@app.command("update-executive-assistant", short_help="Modify Executive Assistant Settings for a Person.")
def update_executive_assistant(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    type_param: str = typer.Option(None, "--type", help="Choices: UNASSIGNED, EXECUTIVE, EXECUTIVE_ASSISTANT"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Executive Assistant Settings for a Person.\n\n\b\nExample: wxcli user-settings update-executive-assistant PERSON_ID\n\n\b\nExample --json-body: '{"type":"UNASSIGNED"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EXECUTIVE_ASSISTANT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/executiveAssistant"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-hoteling", short_help="Read Hoteling Settings for a Person.")
def show_hoteling(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Hoteling Settings for a Person.\n\n\b\nExample: wxcli user-settings show-hoteling PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/hoteling"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_HOTELING = '{"enabled":true}'

@app.command("update-hoteling", short_help="Configure Hoteling Settings for a Person.")
def update_hoteling(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="When `true`, allow this person to connect to a Hoteling host device."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Hoteling Settings for a Person.\n\n\b\nExample: wxcli user-settings update-hoteling PERSON_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_HOTELING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/hoteling"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-available-members-speed-dials", short_help="Get Available Speed Dials for Person Monitoring.")
def list_available_members_speed_dials(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    location_id: str = typer.Option(None, "--location-id", help="Search for the available speed dials in the location ID."),
    member_name: str = typer.Option(None, "--member-name", help="Search for available members by name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for available members by number or extension."),
    order: str = typer.Option(None, "--order", help="Sort response based on `firstName` or `lastName` with sort direction `asc` or `desc`. Example: `lastName-asc` or `firstName-desc`. Default sort is ascending order."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Speed Dials for Person Monitoring.\n\n\b\nExample: wxcli user-settings list-available-members-speed-dials PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/monitoring/speedDials/availableMembers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber')], limit=limit)



@app.command("list-available-members-monitoring", short_help="Get Available Members for Person Monitoring.")
def list_available_members_monitoring(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    location_id: str = typer.Option(None, "--location-id", help="Search for the available members in the location ID."),
    member_name: str = typer.Option(None, "--member-name", help="Search for available members by name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for available members by number or extension."),
    order: str = typer.Option(None, "--order", help="Sort response based on `firstName` or `lastName` with sort direction `asc` or `desc`. Example: `lastName-asc` or `firstName-desc`. Default sort is ascending order."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Members for Person Monitoring.\n\n\b\nExample: wxcli user-settings list-available-members-monitoring PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/monitoring/availableMembers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber')], limit=limit)



@app.command("show-incoming-permission", short_help="Read Incoming Permission Settings for a Person.")
def show_incoming_permission(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Incoming Permission Settings for a Person.\n\n\b\nExample: wxcli user-settings show-incoming-permission PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/incomingPermission"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_INCOMING_PERMISSION = '{"useCustomEnabled":true,"externalTransfer":"ALLOW_ALL_EXTERNAL","internalCallsEnabled":true,"collectCallsEnabled":true}'

@app.command("update-incoming-permission", short_help="Configure Incoming Permission Settings for a Person.")
def update_incoming_permission(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help="When true, indicates that this virtual line uses the specified calling permissions for receiving inbound calls rather than the organizational defaults."),
    external_transfer: str = typer.Option(None, "--external-transfer", help="Choices: ALLOW_ALL_EXTERNAL, ALLOW_ONLY_TRANSFERRED_EXTERNAL, BLOCK_ALL_EXTERNAL"),
    internal_calls_enabled: bool = typer.Option(None, "--internal-calls-enabled/--no-internal-calls-enabled", help="Internal calls are allowed to be received."),
    collect_calls_enabled: bool = typer.Option(None, "--collect-calls-enabled/--no-collect-calls-enabled", help="Collect calls are allowed to be received."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Incoming Permission Settings for a Person.\n\n\b\nExample: wxcli user-settings update-incoming-permission PERSON_ID --use-custom-enabled --external-transfer ALLOW_ALL_EXTERNAL --internal-calls-enabled --collect-calls-enabled\n\n\b\nExample --json-body: '{"useCustomEnabled":true,"externalTransfer":"ALLOW_ALL_EXTERNAL","internalCallsEnabled":true,"collectCallsEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_INCOMING_PERMISSION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/incomingPermission"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-outgoing-permission", short_help="Retrieve a person's Outgoing Calling Permissions Settings.")
def list_outgoing_permission(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a person's Outgoing Calling Permissions Settings.\n\n\b\nExample: wxcli user-settings list-outgoing-permission PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/outgoingPermission"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("callingPermissions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Call Type', 'callType'), ('Action', 'action'), ('Transfer Enabled', 'transferEnabled'), ('Is Call Type Restriction Enabled', 'isCallTypeRestrictionEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_OUTGOING_PERMISSION = '{"callingPermissions":[{"transferEnabled":true,"callType":"INTERNAL_CALL","action":"ALLOW"}],"useCustomEnabled":true,"useCustomPermissions":true}'

@app.command("update-outgoing-permission", short_help="Modify a person's Outgoing Calling Permissions Settings.")
def update_outgoing_permission(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help="When true, indicates that this user uses the shared control that applies to all outgoing call settings categories when placing outbound calls."),
    use_custom_permissions: bool = typer.Option(None, "--use-custom-permissions/--no-use-custom-permissions", help="When true, indicates that this user uses the specified outgoing calling permissions when placing outbound calls."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a person's Outgoing Calling Permissions Settings.\n\n\b\nExample: wxcli user-settings update-outgoing-permission PERSON_ID --json-body '{"callingPermissions":[{"transferEnabled":true}]}'\n\n\b\nExample --json-body: '{"callingPermissions":[{"transferEnabled":true,"callType":"INTERNAL_CALL","action":"ALLOW"}],"useCustomEnabled":true,"useCustomPermissions":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_OUTGOING_PERMISSION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/outgoingPermission"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if use_custom_enabled is not None:
            body["useCustomEnabled"] = use_custom_enabled
        if use_custom_permissions is not None:
            body["useCustomPermissions"] = use_custom_permissions
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-numbers", short_help="Get a List of Phone Numbers for a Person.")
def list_numbers(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    prefer_e164_format: str = typer.Option(None, "--prefer-e164-format", help="Return phone numbers in E.164 format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a List of Phone Numbers for a Person.\n\n\b\nExample: wxcli user-settings list-numbers PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/numbers"
    params = {}
    if prefer_e164_format is not None:
        params["preferE164Format"] = prefer_e164_format
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Number', 'directNumber'), ('Extension', 'extension'), ('Primary', 'primary')], limit=limit)



@app.command("list-privacy", short_help="Get a person's Privacy Settings.")
def list_privacy(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a person's Privacy Settings.\n\n\b\nExample: wxcli user-settings list-privacy PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/privacy"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("monitoringAgents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Last Name', 'lastName'), ('First Name', 'firstName'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_UPDATE_PRIVACY = '{"aaExtensionDialingEnabled":true,"aaNamingDialingEnabled":true,"enablePhoneStatusDirectoryPrivacy":true,"enablePhoneStatusPickupBargeInPrivacy":true,"monitoringAgents":["..."]}'

@app.command("update-privacy", short_help="Configure a person's Privacy Settings.")
def update_privacy(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    aa_extension_dialing_enabled: bool = typer.Option(None, "--aa-extension-dialing-enabled/--no-aa-extension-dialing-enabled", help="When `true` auto attendant extension dialing is enabled."),
    aa_naming_dialing_enabled: bool = typer.Option(None, "--aa-naming-dialing-enabled/--no-aa-naming-dialing-enabled", help="When `true` auto attendant dailing by first or last name is enabled."),
    enable_phone_status_directory_privacy: bool = typer.Option(None, "--enable-phone-status-directory-privacy/--no-enable-phone-status-directory-privacy", help="When `true` phone status directory privacy is enabled."),
    enable_phone_status_pickup_barge_in_privacy: bool = typer.Option(None, "--enable-phone-status-pickup-barge-in-privacy/--no-enable-phone-status-pickup-barge-in-privacy", help="When `true` privacy is enforced for call pickup and barge-in. Only members specified by `monitoringAgents` can pickup or barge-in on the call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure a person's Privacy Settings.\n\n\b\nExample: wxcli user-settings update-privacy PERSON_ID\n\n\b\nExample --json-body: '{"aaExtensionDialingEnabled":true,"aaNamingDialingEnabled":true,"enablePhoneStatusDirectoryPrivacy":true,"enablePhoneStatusPickupBargeInPrivacy":true,"monitoringAgents":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PRIVACY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/privacy"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-push-to-talk", short_help="Read Push-to-Talk Settings for a Person.")
def list_push_to_talk(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Push-to-Talk Settings for a Person.\n\n\b\nExample: wxcli user-settings list-push-to-talk PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/pushToTalk"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Last Name', 'lastName'), ('First Name', 'firstName'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_UPDATE_PUSH_TO_TALK = '{"allowAutoAnswer":true,"connectionType":"ONE_WAY","accessType":"ALLOW_MEMBERS","members":["..."]}'

@app.command("update-push-to-talk", short_help="Configure Push-to-Talk Settings for a Person.")
def update_push_to_talk(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    allow_auto_answer: bool = typer.Option(None, "--allow-auto-answer/--no-allow-auto-answer", help="`true` if Push-to-Talk feature is enabled."),
    connection_type: str = typer.Option(None, "--connection-type", help="Choices: ONE_WAY, TWO_WAY"),
    access_type: str = typer.Option(None, "--access-type", help="Choices: ALLOW_MEMBERS, BLOCK_MEMBERS"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Push-to-Talk Settings for a Person.\n\n\b\nExample: wxcli user-settings update-push-to-talk PERSON_ID\n\n\b\nExample --json-body: '{"allowAutoAnswer":true,"connectionType":"ONE_WAY","accessType":"ALLOW_MEMBERS","members":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PUSH_TO_TALK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/pushToTalk"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if allow_auto_answer is not None:
            body["allowAutoAnswer"] = allow_auto_answer
        if connection_type is not None:
            body["connectionType"] = connection_type
        if access_type is not None:
            body["accessType"] = access_type
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-reception", short_help="Read Receptionist Client Settings for a Person.")
def list_reception(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Receptionist Client Settings for a Person.\n\n\b\nExample: wxcli user-settings list-reception PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/reception"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("monitoredMembers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Last Name', 'lastName'), ('First Name', 'firstName'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_UPDATE_RECEPTION = '{"receptionEnabled":true,"monitoredMembers":["..."]}'

@app.command("update-reception", short_help="Configure Receptionist Client Settings for a Person.")
def update_reception(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    reception_enabled: bool = typer.Option(None, "--reception-enabled/--no-reception-enabled", help="`true` if the Receptionist Client feature is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Receptionist Client Settings for a Person.\n\n\b\nExample: wxcli user-settings update-reception PERSON_ID --reception-enabled\n\n\b\nExample --json-body: '{"receptionEnabled":true,"monitoredMembers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_RECEPTION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/reception"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if reception_enabled is not None:
            body["receptionEnabled"] = reception_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-schedules", short_help="List of Schedules for a Person.")
def list_schedules(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    name: str = typer.Option(None, "--name", help="Specifies the case insensitive substring to be matched against the schedule names. The maximum length is 40."),
    type_param: str = typer.Option(None, "--type", help="Specifies the schedule event type to be matched on the given type."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List of Schedules for a Person.\n\n\b\nExample: wxcli user-settings list-schedules PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules"
    params = {}
    if name is not None:
        params["name"] = name
    if type_param is not None:
        params["type"] = type_param
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("schedules", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="schedules"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Level', 'level')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","type":"businessHours","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":0},"recurWeekly":{"recurInterval":0,"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true}}}]}'

@app.command("create", short_help="Create Schedule for a Person.")
def create(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    name: str = typer.Option(None, "--name", help="(required) Name for the schedule."),
    type_param: str = typer.Option(None, "--type", help="(required) Choices: businessHours, holidays"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Schedule for a Person.\n\n\b\nExample: wxcli user-settings create PERSON_ID --name NAME --type businessHours\n\n\b\nExample --json-body: '{"name":"...","type":"businessHours","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":0},"recurWeekly":{"recurInterval":0,"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true}}}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if type_param is not None:
            body["type"] = type_param
        _missing = [f for f in ['name', 'type'] if f not in body or body[f] is None]
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



@app.command("show-schedules", short_help="Get a Schedule Details.")
def show_schedules(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_type: str = typer.Argument(help="from: wxcli user-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli user-settings list-schedules"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Schedule Details.\n\n\b\nExample: wxcli user-settings show-schedules PERSON_ID SCHEDULE_TYPE SCHEDULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SCHEDULES = '{"newName":"...","name":"...","type":"businessHours","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":0},"recurWeekly":{"recurInterval":0,"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true}}}]}'

@app.command("update-schedules", short_help="Update a Schedule.")
def update_schedules(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_type: str = typer.Argument(help="from: wxcli user-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli user-settings list-schedules"),
    new_name: str = typer.Option(None, "--new-name", help="New name for the schedule."),
    name: str = typer.Option(None, "--name", help="Name for the schedule."),
    type_param: str = typer.Option(None, "--type", help="Choices: businessHours, holidays"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Schedule.\n\n\b\nExample: wxcli user-settings update-schedules PERSON_ID SCHEDULE_TYPE SCHEDULE_ID --new-name NEW_NAME --name NAME --type businessHours\n\n\b\nExample --json-body: '{"newName":"...","name":"...","type":"businessHours","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":0},"recurWeekly":{"recurInterval":0,"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true}}}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SCHEDULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if new_name is not None:
            body["newName"] = new_name
        if name is not None:
            body["name"] = name
        if type_param is not None:
            body["type"] = type_param
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
        emit({"status": "updated", "id": schedule_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Schedule.")
def delete(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_type: str = typer.Argument(help="from: wxcli user-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli user-settings list-schedules"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Schedule.\n\n\b\nExample: wxcli user-settings delete PERSON_ID SCHEDULE_TYPE SCHEDULE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {schedule_id}?", abort=True)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {schedule_id}")
    else:
        emit({"status": "deleted", "id": schedule_id}, output=output, fields=fields)



@app.command("show-events", short_help="Fetch Event for a person's Schedule.")
def show_events(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_type: str = typer.Argument(help="from: wxcli user-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli user-settings list-schedules"),
    event_id: str = typer.Argument(help="Webex USER_SCHEDULE_EVENT id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch Event for a person's Schedule.\n\n\b\nExample: wxcli user-settings show-events PERSON_ID SCHEDULE_TYPE SCHEDULE_ID EVENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_EVENTS = '{"newName":"...","name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":0},"recurWeekly":{"recurInterval":0,"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true}}}'

@app.command("update-events", short_help="Update an Event for a person's Schedule.")
def update_events(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_type: str = typer.Argument(help="from: wxcli user-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli user-settings list-schedules"),
    event_id: str = typer.Argument(help="Webex USER_SCHEDULE_EVENT id"),
    new_name: str = typer.Option(None, "--new-name", help="New name for the event."),
    name: str = typer.Option(None, "--name", help="Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="Start date of the event, or first occurrence if repeating, in the format of YYYY-MM-DD. This field is required if the `allDayEnabled` field is present."),
    end_date: str = typer.Option(None, "--end-date", help="End date of the event, or first occurrence if repeating, in the format of YYYY-MM-DD. This field is required if the `allDayEnabled` field is present."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of the event in the format of HH:MM (24 hours format). This field is required if the `allDayEnabled` field is false or omitted."),
    end_time: str = typer.Option(None, "--end-time", help="End time of the event in the format of HH:MM (24 hours format). This field is required if the `allDayEnabled` field is false or omitted."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="True if it is all-day event."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Event for a person's Schedule.\n\n\b\nExample: wxcli user-settings update-events PERSON_ID SCHEDULE_TYPE SCHEDULE_ID EVENT_ID --new-name NEW_NAME --name NAME --start-date START_DATE --end-date END_DATE --start-time START_TIME --end-time END_TIME\n\n\b\nExample --json-body: '{"newName":"...","name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":0},"recurWeekly":{"recurInterval":0,"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EVENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": event_id}, output=output, fields=fields)



@app.command("delete-events", short_help="Delete an Event for a person's Schedule.")
def delete_events(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_type: str = typer.Argument(help="from: wxcli user-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli user-settings list-schedules"),
    event_id: str = typer.Argument(help="Webex USER_SCHEDULE_EVENT id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an Event for a person's Schedule.\n\n\b\nExample: wxcli user-settings delete-events PERSON_ID SCHEDULE_TYPE SCHEDULE_ID EVENT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {event_id}?", abort=True)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {event_id}")
    else:
        emit({"status": "deleted", "id": event_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_EVENTS = '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":0},"recurWeekly":{"recurInterval":0,"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true}}}'

@app.command("create-events", short_help="Add a New Event for Person's Schedule.")
def create_events(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_type: str = typer.Argument(help="from: wxcli user-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli user-settings list-schedules"),
    name: str = typer.Option(None, "--name", help="(required) Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="(required) Start date of the event, or first occurrence if repeating, in the format of `YYYY-MM-DD`. This field is required if the `allDayEnabled` field is present."),
    end_date: str = typer.Option(None, "--end-date", help="(required) End date of the event, or first occurrence if repeating, in the format of `YYYY-MM-DD`. This field is required if the `allDayEnabled` field is present."),
    start_time: str = typer.Option(None, "--start-time", help="(required) Start time of the event in the format of `HH:MM` (24 hours format). This field is required if the `allDayEnabled` field is false or omitted."),
    end_time: str = typer.Option(None, "--end-time", help="(required) End time of the event in the format of `HH:MM` (24 hours format). This field is required if the `allDayEnabled` field is false or omitted."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="True if it is all-day event."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a New Event for Person's Schedule.\n\n\b\nExample: wxcli user-settings create-events PERSON_ID SCHEDULE_TYPE SCHEDULE_ID --name NAME --start-date START_DATE --end-date END_DATE --start-time START_TIME --end-time END_TIME\n\n\b\nExample --json-body: '{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":true,"recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":0},"recurWeekly":{"recurInterval":0,"sunday":true,"monday":true,"tuesday":true,"wednesday":true,"thursday":true,"friday":true,"saturday":true}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_EVENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/schedules/{schedule_type}/{schedule_id}/events"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        _missing = [f for f in ['name', 'startDate', 'endDate', 'startTime', 'endTime'] if f not in body or body[f] is None]
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



@app.command("show-voicemail", short_help="Read Voicemail Settings for a Person.")
def show_voicemail(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Voicemail Settings for a Person.\n\n\b\nExample: wxcli user-settings show-voicemail PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_VOICEMAIL = '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."},"faxMessage":{"enabled":true,"phoneNumber":"...","extension":"..."}}'

@app.command("update-voicemail", short_help="Configure Voicemail Settings for a Person.")
def update_voicemail(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Voicemail is enabled or disabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Voicemail Settings for a Person.\n\n\b\nExample: wxcli user-settings update-voicemail PERSON_ID --json-body '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."}}'\n\n\b\nExample --json-body: '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."},"faxMessage":{"enabled":true,"phoneNumber":"...","extension":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VOICEMAIL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("configure-busy-voicemail", short_help="Configure Busy Voicemail Greeting for a Person.")
def configure_busy_voicemail(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Busy Voicemail Greeting for a Person.\n\n\b\nExample: wxcli user-settings configure-busy-voicemail PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail/actions/uploadBusyGreeting/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    emit(result, output=output, fields=fields)



@app.command("configure-no-answer", short_help="Configure No Answer Voicemail Greeting for a Person.")
def configure_no_answer(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure No Answer Voicemail Greeting for a Person.\n\n\b\nExample: wxcli user-settings configure-no-answer PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail/actions/uploadNoAnswerGreeting/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    emit(result, output=output, fields=fields)



@app.command("reset-voicemail-pin", short_help="Reset Voicemail PIN.")
def reset_voicemail_pin(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reset Voicemail PIN.\n\n\b\nExample: wxcli user-settings reset-voicemail-pin PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/voicemail/actions/resetPin/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    emit(result, output=output, fields=fields)



@app.command("list-move-location", short_help="List Move Users Jobs.")
def list_move_location(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Move Users Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Tracking ID', 'trackingId'), ('Source User ID', 'sourceUserId'), ('Source Customer ID', 'sourceCustomerId'), ('Target Customer ID', 'targetCustomerId')], limit=limit)



_BODY_SKELETON_CREATE_MOVE_LOCATION = '{"usersList":[{"locationId":"...","validate":true,"users":[{"userId":"...","extension":"...","phoneNumber":"..."}]}]}'

@app.command("create-move-location", short_help="Validate or Initiate Move Users Job.")
def create_move_location(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate or Initiate Move Users Job.\n\n\b\nExample: wxcli user-settings create-move-location --json-body '{"usersList":[{"locationId":"...","validate":true,"users":[{"userId":"..."}]}]}'\n\n\b\nExample --json-body: '{"usersList":[{"locationId":"...","validate":true,"users":[{"userId":"...","extension":"...","phoneNumber":"..."}]}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_MOVE_LOCATION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        if isinstance(result, dict) and "response" in result:
            typer.echo(f"Created: {result['response']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("show-move-location", short_help="Get Move Users Job Status.")
def show_move_location(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli user-settings list-move-location"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Move Users Job Status.\n\n\b\nExample: wxcli user-settings show-move-location JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation/{job_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("pause-the-move", short_help="Pause the Move Users Job.")
def pause_the_move(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli user-settings list-move-location"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause the Move Users Job.\n\n\b\nExample: wxcli user-settings pause-the-move JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation/{job_id}/actions/pause/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    emit(result, output=output, fields=fields)



@app.command("resume-the-move", short_help="Resume the Move Users Job.")
def resume_the_move(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli user-settings list-move-location"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume the Move Users Job.\n\n\b\nExample: wxcli user-settings resume-the-move JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation/{job_id}/actions/resume/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    emit(result, output=output, fields=fields)



@app.command("list-errors", short_help="List Move Users Job errors.")
def list_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli user-settings list-move-location"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Move Users Job errors.\n\n\b\nExample: wxcli user-settings list-errors JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/person/moveLocation/{job_id}/errors"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Tracking ID', 'trackingId'), ('Item', 'item'), ('Item Number', 'itemNumber')], limit=limit)



@app.command("show-music-on-hold", short_help="Retrieve Music On Hold Settings for a Person.")
def show_music_on_hold(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Music On Hold Settings for a Person.\n\n\b\nExample: wxcli user-settings show-music-on-hold PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/musicOnHold"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_MUSIC_ON_HOLD = '{"mohEnabled":true,"greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}}'

@app.command("update-music-on-hold", short_help="Configure Music On Hold Settings for a Person.")
def update_music_on_hold(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    moh_enabled: bool = typer.Option(None, "--moh-enabled/--no-moh-enabled", help="Music on hold is enabled or disabled for the workspace."),
    greeting: str = typer.Option(None, "--greeting", help="Choices: DEFAULT, CUSTOM"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Music On Hold Settings for a Person.\n\n\b\nExample: wxcli user-settings update-music-on-hold PERSON_ID\n\n\b\nExample --json-body: '{"mohEnabled":true,"greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MUSIC_ON_HOLD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/musicOnHold"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if moh_enabled is not None:
            body["mohEnabled"] = moh_enabled
        if greeting is not None:
            body["greeting"] = greeting
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-access-codes", short_help="Retrieve Access Codes for a Person.")
def list_access_codes(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Access Codes for a Person.\n\n\b\nExample: wxcli user-settings list-access-codes PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/accessCodes"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("accessCodes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Code', 'code'), ('Description', 'description')], limit=limit)



_BODY_SKELETON_CREATE_ACCESS_CODES = '{"code":"...","description":"..."}'

@app.command("create-access-codes", short_help="Create Access Codes for a Person.")
def create_access_codes(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    code: str = typer.Option(None, "--code", help="(required) An Access code."),
    description: str = typer.Option(None, "--description", help="(required) The description of the access code."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Access Codes for a Person.\n\n\b\nExample: wxcli user-settings create-access-codes PERSON_ID --code CODE --description DESCRIPTION\n\n\b\nExample --json-body: '{"code":"...","description":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ACCESS_CODES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/accessCodes"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if code is not None:
            body["code"] = code
        if description is not None:
            body["description"] = description
        _missing = [f for f in ['code', 'description'] if f not in body or body[f] is None]
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



_BODY_SKELETON_UPDATE_ACCESS_CODES = '{"deleteCodes":["..."]}'

@app.command("update-access-codes", short_help="Modify Access Codes for a Person.")
def update_access_codes(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Access Codes for a Person.\n\nDESTRUCTIVE: this PUT only deletes despite the summary above. It cannot add or modify.\n\n\b\nExample: wxcli user-settings update-access-codes PERSON_ID\n\n\b\nExample --json-body: '{"deleteCodes":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ACCESS_CODES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/accessCodes"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        typer.echo(f"Deleted.")
    else:
        emit({"status": "deleted", "id": person_id}, output=output, fields=fields)



@app.command("delete-access-codes", short_help="Delete Access Codes for a Person.")
def delete_access_codes(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Access Codes for a Person.\n\n\b\nExample: wxcli user-settings delete-access-codes PERSON_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Access Codes for {person_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/accessCodes"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {person_id}")
    else:
        emit({"status": "deleted", "id": person_id}, output=output, fields=fields)



@app.command("show-auto-transfer-numbers", short_help="Retrieve Transfer Numbers for a Person.")
def show_auto_transfer_numbers(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Transfer Numbers for a Person.\n\n\b\nExample: wxcli user-settings show-auto-transfer-numbers PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/autoTransferNumbers"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_AUTO_TRANSFER_NUMBERS = '{"useCustomTransferNumbers":true,"autoTransferNumber1":"...","autoTransferNumber2":"...","autoTransferNumber3":"..."}'

@app.command("update-auto-transfer-numbers", short_help="Modify Transfer Numbers for a Person.")
def update_auto_transfer_numbers(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    use_custom_transfer_numbers: bool = typer.Option(None, "--use-custom-transfer-numbers/--no-use-custom-transfer-numbers", help="When `true`, use custom settings for the transfer numbers category of outbound permissions."),
    auto_transfer_number1: str = typer.Option(None, "--auto-transfer-number1", help="When calling a specific call type, this workspace will be automatically transferred to another number."),
    auto_transfer_number2: str = typer.Option(None, "--auto-transfer-number2", help="When calling a specific call type, this workspace will be automatically transferred to another number."),
    auto_transfer_number3: str = typer.Option(None, "--auto-transfer-number3", help="When calling a specific call type, this workspace will be automatically transferred to another number."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Transfer Numbers for a Person.\n\n\b\nExample: wxcli user-settings update-auto-transfer-numbers PERSON_ID --use-custom-transfer-numbers\n\n\b\nExample --json-body: '{"useCustomTransferNumbers":true,"autoTransferNumber1":"...","autoTransferNumber2":"...","autoTransferNumber3":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_AUTO_TRANSFER_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/autoTransferNumbers"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-digit-patterns", short_help="Retrieve Digit Patterns for a Person.")
def list_digit_patterns(
    person_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Digit Patterns for a Person.\n\n\b\nExample: wxcli user-settings list-digit-patterns PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("digitPatterns", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Pattern', 'pattern'), ('Action', 'action'), ('Transfer Enabled', 'transferEnabled')], limit=limit)



_BODY_SKELETON_CREATE_DIGIT_PATTERNS = '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'

@app.command("create-digit-patterns", short_help="Create Digit Patterns for a Person.")
def create_digit_patterns(
    person_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli people list"),
    name: str = typer.Option(None, "--name", help="(required) A unique name for the digit pattern."),
    pattern: str = typer.Option(None, "--pattern", help="(required) The digit pattern to be matched with the input number."),
    action: str = typer.Option(None, "--action", help="(required) Choices: ALLOW, BLOCK, AUTH_CODE, TRANSFER_NUMBER_1, TRANSFER_NUMBER_2, TRANSFER_NUMBER_3"),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help="(required) If `true`, allows transfer and forwarding for the call type."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Digit Patterns for a Person.\n\n\b\nExample: wxcli user-settings create-digit-patterns PERSON_ID --name NAME --pattern PATTERN --action ALLOW --transfer-enabled\n\n\b\nExample --json-body: '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DIGIT_PATTERNS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        _missing = [f for f in ['name', 'pattern', 'action', 'transferEnabled'] if f not in body or body[f] is None]
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



_BODY_SKELETON_UPDATE_DIGIT_PATTERNS_OUTGOING_PERMISSION = '{"useCustomDigitPatterns":true}'

@app.command("update-digit-patterns-outgoing-permission", short_help="Modify the Digit Pattern Category Control Settings for a Person.")
def update_digit_patterns_outgoing_permission(
    person_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli people list"),
    use_custom_digit_patterns: bool = typer.Option(None, "--use-custom-digit-patterns/--no-use-custom-digit-patterns", help="When `true`, use custom settings for the digit patterns category of outgoing call permissions."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify the Digit Pattern Category Control Settings for a Person.\n\n\b\nExample: wxcli user-settings update-digit-patterns-outgoing-permission PERSON_ID\n\n\b\nExample --json-body: '{"useCustomDigitPatterns":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DIGIT_PATTERNS_OUTGOING_PERMISSION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if use_custom_digit_patterns is not None:
            body["useCustomDigitPatterns"] = use_custom_digit_patterns
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("delete-digit-patterns-outgoing-permission", short_help="Delete all Digit Patterns for a Person.")
def delete_digit_patterns_outgoing_permission(
    person_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli people list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete all Digit Patterns for a Person.\n\n\b\nExample: wxcli user-settings delete-digit-patterns-outgoing-permission PERSON_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Digit Patterns for {person_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {person_id}")
    else:
        emit({"status": "deleted", "id": person_id}, output=output, fields=fields)



@app.command("show-digit-patterns", short_help="Retrieve Digit Pattern Details for a Person.")
def show_digit_patterns(
    person_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli people list"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli user-settings list-digit-patterns"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Digit Pattern Details for a Person.\n\n\b\nExample: wxcli user-settings show-digit-patterns PERSON_ID DIGIT_PATTERN_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_DIGIT_PATTERNS_OUTGOING_PERMISSION_1 = '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'

@app.command("update-digit-patterns-outgoing-permission-1", short_help="Modify a Digit Pattern for a Person.")
def update_digit_patterns_outgoing_permission_1(
    person_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli people list"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli user-settings list-digit-patterns"),
    name: str = typer.Option(None, "--name", help="A unique name for the digit pattern."),
    pattern: str = typer.Option(None, "--pattern", help="The digit pattern to be matched with the input number."),
    action: str = typer.Option(None, "--action", help="Choices: ALLOW, BLOCK, AUTH_CODE, TRANSFER_NUMBER_1, TRANSFER_NUMBER_2, TRANSFER_NUMBER_3"),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help="If `true`, allows transfer and forwarding for the call type."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Digit Pattern for a Person.\n\n\b\nExample: wxcli user-settings update-digit-patterns-outgoing-permission-1 PERSON_ID DIGIT_PATTERN_ID\n\n\b\nExample --json-body: '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DIGIT_PATTERNS_OUTGOING_PERMISSION_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": digit_pattern_id}, output=output, fields=fields)



@app.command("delete-digit-patterns-outgoing-permission-1", short_help="Delete a Digit Pattern for a Person.")
def delete_digit_patterns_outgoing_permission_1(
    person_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli people list"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli user-settings list-digit-patterns"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Digit Pattern for a Person.\n\n\b\nExample: wxcli user-settings delete-digit-patterns-outgoing-permission-1 PERSON_ID DIGIT_PATTERN_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {digit_pattern_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {digit_pattern_id}")
    else:
        emit({"status": "deleted", "id": digit_pattern_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_NUMBERS = '{"phoneNumbers":[{"primary":true,"action":"ADD","directNumber":"...","extension":"...","ringPattern":"NORMAL"}],"distinctiveRingEnabled":true}'

@app.command("update-numbers", short_help="Assign or Unassign numbers to a person.")
def update_numbers(
    person_id: str = typer.Argument(help="from: wxcli people list"),
    distinctive_ring_enabled: bool = typer.Option(None, "--distinctive-ring-enabled/--no-distinctive-ring-enabled", help="Enables a distinctive ring pattern for the person."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign or Unassign numbers to a person.\n\n\b\nExample: wxcli user-settings update-numbers PERSON_ID --json-body '{"phoneNumbers":[{"primary":true,"action":"ADD","directNumber":"..."}]}'\n\n\b\nExample --json-body: '{"phoneNumbers":[{"primary":true,"action":"ADD","directNumber":"...","extension":"...","ringPattern":"NORMAL"}],"distinctiveRingEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/numbers"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if distinctive_ring_enabled is not None:
            body["distinctiveRingEnabled"] = distinctive_ring_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-preferred-answer-endpoint", short_help="Get Preferred Answer Endpoint.")
def list_preferred_answer_endpoint(
    person_id: str = typer.Argument(help="from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Preferred Answer Endpoint.\n\n\b\nExample: wxcli user-settings list-preferred-answer-endpoint PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/preferredAnswerEndpoint"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("endpoints", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_UPDATE_PREFERRED_ANSWER_ENDPOINT = '{"preferredAnswerEndpointId":"..."}'

@app.command("update-preferred-answer-endpoint", short_help="Modify Preferred Answer Endpoint.")
def update_preferred_answer_endpoint(
    person_id: str = typer.Argument(help="from: wxcli people list"),
    preferred_answer_endpoint_id: str = typer.Option(None, "--preferred-answer-endpoint-id", help="Person’s preferred answer endpoint."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Preferred Answer Endpoint.\n\n\b\nExample: wxcli user-settings update-preferred-answer-endpoint PERSON_ID --preferred-answer-endpoint-id PREFERRED_ANSWER_ENDPOINT_ID\n\n\b\nExample --json-body: '{"preferredAnswerEndpointId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PREFERRED_ANSWER_ENDPOINT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/preferredAnswerEndpoint"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if preferred_answer_endpoint_id is not None:
            body["preferredAnswerEndpointId"] = preferred_answer_endpoint_id
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-available-members-applications", short_help="Search Shared-Line Appearance Members.")
def list_available_members_applications(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    application_id: str = typer.Argument(help="applicationId"),
    location: str = typer.Option(None, "--location", help="Location ID for the user."),
    name: str = typer.Option(None, "--name", help="Search for users whose names match the query."),
    number: str = typer.Option(None, "--number", help="Search for users whose numbers match the query."),
    order: str = typer.Option(None, "--order", help="Sort by first name (`fname`) or last name (`lname`)."),
    extension: str = typer.Option(None, "--extension", help="Search for users whose extensions match the query."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Shared-Line Appearance Members.\n\n\b\nExample: wxcli user-settings list-available-members-applications PERSON_ID APPLICATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/{application_id}/availableMembers"
    params = {}
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-members-applications", short_help="Get Shared-Line Appearance Members.")
def list_members_applications(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    application_id: str = typer.Argument(help="applicationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Shared-Line Appearance Members.\n\n\b\nExample: wxcli user-settings list-members-applications PERSON_ID APPLICATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/{application_id}/members"
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
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE_MEMBERS_APPLICATIONS = '{"members":[{"id":"...","port":0,"primaryOwner":"...","lineType":"PRIMARY","lineWeight":0,"hotlineEnabled":true,"hotlineDestination":"...","allowCallDeclineEnabled":true,"t38FaxCompressionEnabled `true`":true,"lineLabel":"..."}]}'

@app.command("update-members-applications", short_help="Put Shared-Line Appearance Members.")
def update_members_applications(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    application_id: str = typer.Argument(help="applicationId"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Put Shared-Line Appearance Members.\n\n\b\nExample: wxcli user-settings update-members-applications PERSON_ID APPLICATION_ID\n\n\b\nExample --json-body: '{"members":[{"id":"...","port":0,"primaryOwner":"...","lineType":"PRIMARY","lineWeight":0,"hotlineEnabled":true,"hotlineDestination":"...","allowCallDeclineEnabled":true,"t38FaxCompressionEnabled `true`":true,"lineLabel":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MEMBERS_APPLICATIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/{application_id}/members"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated", "id": application_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_PASSCODE = '{"passcode":"..."}'

@app.command("update-passcode", short_help="Modify a person's voicemail passcode.")
def update_passcode(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    passcode: str = typer.Option(None, "--passcode", help="Voicemail access passcode. The minimum length of the passcode is 6 and the maximum length is 30."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a person's voicemail passcode.\n\n\b\nExample: wxcli user-settings update-passcode PERSON_ID --passcode PASSCODE\n\n\b\nExample --json-body: '{"passcode":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PASSCODE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/voicemail/passcode"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if passcode is not None:
            body["passcode"] = passcode
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-summary", short_help="Get Message Summary.")
def show_summary(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Message Summary."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/summary"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-voice-messages", short_help="List Messages.")
def list_voice_messages(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Duration', 'duration'), ('Urgent', 'urgent'), ('Confidential', 'confidential'), ('Read', 'read')], limit=limit)



@app.command("delete-voice-messages", short_help="Delete Message.")
def delete_voice_messages(
    message_id: str = typer.Argument(help="from: wxcli user-settings list-voice-messages"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Message.\n\n\b\nExample: wxcli user-settings delete-voice-messages MESSAGE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {message_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/{message_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {message_id}")
    else:
        emit({"status": "deleted", "id": message_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_MARK_AS_READ = '{"messageId":"...","lineOwnerId":"..."}'

@app.command("create-mark-as-read", short_help="Mark As Read.")
def create_mark_as_read(
    message_id: str = typer.Option(None, "--message-id", help="The voicemail message identifier of the message to mark as read. If the `messageId` is not provided, then all voicemail messages for the user are marked as read."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mark As Read.\n\n\b\nExample --json-body: '{"messageId":"...","lineOwnerId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_MARK_AS_READ), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/markAsRead"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if message_id is not None:
            body["messageId"] = message_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



_BODY_SKELETON_CREATE_MARK_AS_UNREAD = '{"messageId":"...","lineOwnerId":"..."}'

@app.command("create-mark-as-unread", short_help="Mark As Unread.")
def create_mark_as_unread(
    message_id: str = typer.Option(None, "--message-id", help="The voicemail message identifier of the message to mark as unread. If the `messageId` is not provided, then all voicemail messages for the user are marked as unread."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mark As Unread.\n\n\b\nExample --json-body: '{"messageId":"...","lineOwnerId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_MARK_AS_UNREAD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/markAsUnread"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if message_id is not None:
            body["messageId"] = message_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



@app.command("list-available-caller-ids", short_help="Retrieve Agent's List of Available Caller IDs.")
def list_available_caller_ids(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Agent's List of Available Caller IDs.\n\n\b\nExample: wxcli user-settings list-available-caller-ids PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/agent/availableCallerIds"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("availableCallerIds", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



@app.command("show-caller-id", short_help="Retrieve Agent's Caller ID Information.")
def show_caller_id(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Agent's Caller ID Information.\n\n\b\nExample: wxcli user-settings show-caller-id PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/agent/callerId"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALLER_ID_AGENT = '{"selectedCallerId":"..."}'

@app.command("update-caller-id-agent", short_help="Modify Agent's Caller ID Information.")
def update_caller_id_agent(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    selected_caller_id: str = typer.Option(None, "--selected-caller-id", help="The unique identifier of the call queue or hunt group to use for the agent's caller ID. Set to null to use the agent's own caller ID."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Agent's Caller ID Information.\n\n\b\nExample: wxcli user-settings update-caller-id-agent PERSON_ID --selected-caller-id SELECTED_CALLER_ID\n\n\b\nExample --json-body: '{"selectedCallerId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALLER_ID_AGENT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/agent/callerId"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if selected_caller_id is not None:
            body["selectedCallerId"] = selected_caller_id
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-call-bridge", short_help="Read Call Bridge Settings for a Person.")
def show_call_bridge(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Bridge Settings for a Person.\n\n\b\nExample: wxcli user-settings show-call-bridge PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/callBridge"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_BRIDGE = '{"warningToneEnabled":true}'

@app.command("update-call-bridge", short_help="Configure Call Bridge Settings for a Person.")
def update_call_bridge(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    warning_tone_enabled: bool = typer.Option(None, "--warning-tone-enabled/--no-warning-tone-enabled", help="Set to enable or disable a stutter dial tone being played to all the participants when a virtual line is bridged on the active shared line call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Bridge Settings for a Person.\n\n\b\nExample: wxcli user-settings update-call-bridge PERSON_ID\n\n\b\nExample --json-body: '{"warningToneEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_BRIDGE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/callBridge"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if warning_tone_enabled is not None:
            body["warningToneEnabled"] = warning_tone_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-available-numbers-secondary", short_help="Get Person Secondary Available Phone Numbers.")
def list_available_numbers_secondary(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Secondary Available Phone Numbers.\n\n\b\nExample: wxcli user-settings list-available-numbers-secondary PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/secondary/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Telephony Type', 'telephonyType'), ('Is Service Number', 'isServiceNumber')], limit=limit)



@app.command("list-available-numbers-fax-message", short_help="Get Person Fax Message Available Phone Numbers.")
def list_available_numbers_fax_message(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Fax Message Available Phone Numbers.\n\n\b\nExample: wxcli user-settings list-available-numbers-fax-message PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/faxMessage/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Telephony Type', 'telephonyType'), ('Is Service Number', 'isServiceNumber')], limit=limit)



@app.command("list-available-numbers-call-forwarding", short_help="Get Person Call Forward Available Phone Numbers.")
def list_available_numbers_call_forwarding(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `extension`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Call Forward Available Phone Numbers.\n\n\b\nExample: wxcli user-settings list-available-numbers-call-forwarding PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/callForwarding/availableNumbers"
    params = {}
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber')], limit=limit)



@app.command("list-available-numbers-primary", short_help="Get Person Primary Available Phone Numbers.")
def list_available_numbers_primary(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of phone numbers for this location within the given organization. The maximum length is 36."),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    license_type: str = typer.Option(None, "--license-type", help="Choices: Webex Calling Professional, Webex Calling Standard"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Primary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/primary/availableNumbers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if license_type is not None:
        params["licenseType"] = license_type
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Telephony Type', 'telephonyType'), ('Mobile Network', 'mobileNetwork')], limit=limit)



@app.command("list-available-numbers-emergency-callback-number", short_help="Get Person ECBN Available Phone Numbers.")
def list_available_numbers_emergency_callback_number(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person ECBN Available Phone Numbers.\n\n\b\nExample: wxcli user-settings list-available-numbers-emergency-callback-number PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if owner_name is not None:
        params["ownerName"] = owner_name
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber'), ('Telephony Type', 'telephonyType')], limit=limit)



@app.command("list-available-numbers-call-intercept", short_help="Get Person Call Intercept Available Phone Numbers.")
def list_available_numbers_call_intercept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `extension`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Call Intercept Available Phone Numbers.\n\n\b\nExample: wxcli user-settings list-available-numbers-call-intercept PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/callIntercept/availableNumbers"
    params = {}
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber')], limit=limit)



@app.command("list-ms-teams", short_help="Retrieve a Person's MS Teams Settings.")
def list_ms_teams(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a Person's MS Teams Settings.\n\n\b\nExample: wxcli user-settings list-ms-teams PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/settings/msTeams"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("settings", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Setting Name', 'settingName'), ('Level', 'level'), ('Value', 'value'), ('Last Modified', 'lastModified')], limit=limit)



_BODY_SKELETON_UPDATE_MS_TEAMS = '{"settingName":"HIDE_WEBEX_APP","value":true}'

@app.command("update-ms-teams", short_help="Configure a Person's MS Teams Setting.")
def update_ms_teams(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    setting_name: str = typer.Option(None, "--setting-name", help="Choices: HIDE_WEBEX_APP"),
    value: bool = typer.Option(None, "--value/--no-value", help="The boolean value to update the `HIDE_WEBEX_APP` setting, either `true` or `false`. Set to `null` to delete the `HIDE_WEBEX_APP` setting."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure a Person's MS Teams Setting.\n\n\b\nExample: wxcli user-settings update-ms-teams PERSON_ID --setting-name HIDE_WEBEX_APP --value\n\n\b\nExample --json-body: '{"settingName":"HIDE_WEBEX_APP","value":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MS_TEAMS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/settings/msTeams"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if setting_name is not None:
            body["settingName"] = setting_name
        if value is not None:
            body["value"] = value
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-personal-assistant", short_help="Get Personal Assistant.")
def show_personal_assistant(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Personal Assistant.\n\n\b\nExample: wxcli user-settings show-personal-assistant PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/personalAssistant"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_PERSONAL_ASSISTANT = '{"enabled":true,"presence":"NONE","untilDateTime":"...","transferEnabled":true,"transferNumber":"...","alerting":"ALERT_ME_FIRST","alertMeFirstNumberOfRings":0}'

@app.command("update-personal-assistant", short_help="Update Personal Assistant.")
def update_personal_assistant(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Toggles feature."),
    presence: str = typer.Option(None, "--presence", help="Choices: NONE, BUSINESS_TRIP, GONE_FOR_THE_DAY, LUNCH, MEETING, OUT_OF_OFFICE, TEMPORARILY_OUT, TRAINING, UNAVAILABLE, VACATION"),
    until_date_time: str = typer.Option(None, "--until-date-time", help="The date until which the personal assistant is active."),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help="If `true`, allows transfer and forwarding for the call type."),
    transfer_number: str = typer.Option(None, "--transfer-number", help="Number to transfer to."),
    alerting: str = typer.Option(None, "--alerting", help="Choices: ALERT_ME_FIRST, PLAY_RING_REMINDER, NONE"),
    alert_me_first_number_of_rings: str = typer.Option(None, "--alert-me-first-number-of-rings", help="Number of rings for alert type: ALERT_ME_FIRST; available range is 2-20."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Personal Assistant.\n\n\b\nExample: wxcli user-settings update-personal-assistant PERSON_ID\n\n\b\nExample --json-body: '{"enabled":true,"presence":"NONE","untilDateTime":"...","transferEnabled":true,"transferNumber":"...","alerting":"ALERT_ME_FIRST","alertMeFirstNumberOfRings":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PERSONAL_ASSISTANT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/personalAssistant"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-available-features", short_help="Retrieve the List of Available Features.")
def list_available_features(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    name: str = typer.Option(None, "--name", help="List features whose `name` contains this string."),
    phone_number: str = typer.Option(None, "--phone-number", help="List features whose phoneNumber contains this matching string."),
    extension: str = typer.Option(None, "--extension", help="List features whose `extension` contains this matching string."),
    order: str = typer.Option(None, "--order", help="Sort the list of features based on `name`, `phoneNumber`, or `extension`, either `asc`, or `desc`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve the List of Available Features.\n\n\b\nExample: wxcli user-settings list-available-features PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/modeManagement/availableFeatures"
    params = {}
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("features", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-mode-management", short_help="Retrieve the List of Features Assigned to a User for Mode Management.")
def list_mode_management(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve the List of Features Assigned to a User for Mode Management.\n\n\b\nExample: wxcli user-settings list-mode-management PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/modeManagement/features"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("features", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE_MODE_MANAGEMENT = '{"featureIds":["..."]}'

@app.command("update-mode-management", short_help="Assign a List of Features to a User for Mode Management.")
def update_mode_management(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign a List of Features to a User for Mode Management.\n\n\b\nExample: wxcli user-settings update-mode-management PERSON_ID --json-body '{"featureIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MODE_MANAGEMENT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/modeManagement/features"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-selective-accept", short_help="Get the User’s Selective Call Accept Criteria List.")
def list_selective_accept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the User’s Selective Call Accept Criteria List.\n\n\b\nExample: wxcli user-settings list-selective-accept PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Schedule Name', 'scheduleName'), ('Source', 'source'), ('Accept Enabled', 'acceptEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SELECTIVE_ACCEPT = '{"enabled":true}'

@app.command("update-selective-accept", short_help="Update User’s Selective Call Accept Criteria.")
def update_selective_accept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="indicates whether selective accept is enabled or not."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User’s Selective Call Accept Criteria.\n\n\b\nExample: wxcli user-settings update-selective-accept PERSON_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_ACCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_ACCEPT = '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("create-criteria-selective-accept", short_help="Create a Criteria to the User’s Selective Call Accept Service.")
def create_criteria_selective_accept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    accept_enabled: bool = typer.Option(None, "--accept-enabled/--no-accept-enabled", help="(required) Boolean flag indicating if selective call accept is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Criteria to the User’s Selective Call Accept Service.\n\n\b\nExample: wxcli user-settings create-criteria-selective-accept PERSON_ID --calls-from ANY_PHONE_NUMBER --accept-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_ACCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept/criteria"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        if accept_enabled is not None:
            body["acceptEnabled"] = accept_enabled
        _missing = [f for f in ['callsFrom', 'acceptEnabled'] if f not in body or body[f] is None]
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



@app.command("show-criteria-selective-accept", short_help="Get a Criteria for the User’s Selective Call Accept Service.")
def show_criteria_selective_accept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Criteria for the User’s Selective Call Accept Service.\n\n\b\nExample: wxcli user-settings show-criteria-selective-accept PERSON_ID ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_ACCEPT = '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("update-criteria-selective-accept", short_help="Modify a Criteria From the User’s Selective Call Accept Service.")
def update_criteria_selective_accept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    accept_enabled: bool = typer.Option(None, "--accept-enabled/--no-accept-enabled", help="Boolean flag to enable/disable the selective accept criteria."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Criteria From the User’s Selective Call Accept Service.\n\n\b\nExample: wxcli user-settings update-criteria-selective-accept PERSON_ID ID --calls-from ANY_PHONE_NUMBER --accept-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_ACCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        if accept_enabled is not None:
            body["acceptEnabled"] = accept_enabled
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
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-selective-accept", short_help="Delete a Criteria From the User’s Selective Call Accept service.")
def delete_criteria_selective_accept(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Criteria From the User’s Selective Call Accept service.\n\n\b\nExample: wxcli user-settings delete-criteria-selective-accept PERSON_ID ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveAccept/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-selective-reject", short_help="Get the User’s Selective Call Rejection Criteria Listing.")
def list_selective_reject(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the User’s Selective Call Rejection Criteria Listing.\n\n\b\nExample: wxcli user-settings list-selective-reject PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Schedule Name', 'scheduleName'), ('Source', 'source'), ('Reject Enabled', 'rejectEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SELECTIVE_REJECT = '{"enabled":true}'

@app.command("update-selective-reject", short_help="Update User’s Selective Call Rejection Criteria List.")
def update_selective_reject(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="if `true`, selective reject is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User’s Selective Call Rejection Criteria List.\n\n\b\nExample: wxcli user-settings update-selective-reject PERSON_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_REJECT = '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("create-criteria-selective-reject", short_help="Create a Criteria to the User’s Selective Call Rejection Service.")
def create_criteria_selective_reject(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, FORWARDED"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    reject_enabled: bool = typer.Option(None, "--reject-enabled/--no-reject-enabled", help="(required) Boolean flag to enable/disable rejection."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Criteria to the User’s Selective Call Rejection Service.\n\n\b\nExample: wxcli user-settings create-criteria-selective-reject PERSON_ID --calls-from ANY_PHONE_NUMBER --reject-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject/criteria"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        if reject_enabled is not None:
            body["rejectEnabled"] = reject_enabled
        _missing = [f for f in ['callsFrom', 'rejectEnabled'] if f not in body or body[f] is None]
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



@app.command("show-criteria-selective-reject", short_help="Get a Criteria for the User’s Selective Call Rejection Service.")
def show_criteria_selective_reject(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Criteria for the User’s Selective Call Rejection Service.\n\n\b\nExample: wxcli user-settings show-criteria-selective-reject PERSON_ID ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_REJECT = '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("update-criteria-selective-reject", short_help="Modify a Criteria for the User’s Selective Call Rejection Service.")
def update_criteria_selective_reject(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, FORWARDED"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    reject_enabled: bool = typer.Option(None, "--reject-enabled/--no-reject-enabled", help="Boolean flag to enable/disable rejection."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Criteria for the User’s Selective Call Rejection Service.\n\n\b\nExample: wxcli user-settings update-criteria-selective-reject PERSON_ID ID --calls-from ANY_PHONE_NUMBER --reject-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        if reject_enabled is not None:
            body["rejectEnabled"] = reject_enabled
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
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-selective-reject", short_help="Delete a Criteria From the User’s Selective Call Rejection Service.")
def delete_criteria_selective_reject(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Criteria From the User’s Selective Call Rejection Service.\n\n\b\nExample: wxcli user-settings delete-criteria-selective-reject PERSON_ID ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveReject/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-selective-forward", short_help="Get the User’s Selective Call Forwarding.")
def list_selective_forward(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the User’s Selective Call Forwarding.\n\n\b\nExample: wxcli user-settings list-selective-forward PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Schedule Name', 'scheduleName'), ('Source', 'source'), ('Ring Enabled', 'ringEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SELECTIVE_FORWARD = '{"enabled":true,"defaultPhoneNumberToForward":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true}'

@app.command("update-selective-forward", short_help="Update User’s Selective Call Forwarding Criteria List.")
def update_selective_forward(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Selective Forward feature is enabled."),
    default_phone_number_to_forward: str = typer.Option(None, "--default-phone-number-to-forward", help="Enter the phone number to forward calls to during this schedule."),
    ring_reminder_enabled: bool = typer.Option(None, "--ring-reminder-enabled/--no-ring-reminder-enabled", help="When `true`, enables a ring reminder for such calls."),
    destination_voicemail_enabled: bool = typer.Option(None, "--destination-voicemail-enabled/--no-destination-voicemail-enabled", help="Enables forwarding for all calls to voicemail. This option is only available for internal phone numbers or extensions."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User’s Selective Call Forwarding Criteria List.\n\n\b\nExample: wxcli user-settings update-selective-forward PERSON_ID\n\n\b\nExample --json-body: '{"enabled":true,"defaultPhoneNumberToForward":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_FORWARD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_FORWARD = '{"forwardToPhoneNumber":"...","sendToVoicemailEnabled":true,"callsFrom":"ANY_PHONE_NUMBER","scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"forwardEnabled":true}'

@app.command("create-criteria-selective-forward", short_help="Create a Criteria to the User’s Selective Call Forwarding Service.")
def create_criteria_selective_forward(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="(required) Number to which calls needs to be forwarded."),
    send_to_voicemail_enabled: bool = typer.Option(None, "--send-to-voicemail-enabled/--no-send-to-voicemail-enabled", help="(required) Boolean flag to enable/disable sending calls to voicemail."),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Calls From custom numbers, private number enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Calls From custom numbers, unavailable number enabled."),
    forward_enabled: bool = typer.Option(None, "--forward-enabled/--no-forward-enabled", help="Boolean flag to enable/disable selective call forward."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Criteria to the User’s Selective Call Forwarding Service.\n\n\b\nExample: wxcli user-settings create-criteria-selective-forward PERSON_ID --forward-to-phone-number FORWARD_TO_PHONE_NUMBER --send-to-voicemail-enabled --calls-from ANY_PHONE_NUMBER\n\n\b\nExample --json-body: '{"forwardToPhoneNumber":"...","sendToVoicemailEnabled":true,"callsFrom":"ANY_PHONE_NUMBER","scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"forwardEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_FORWARD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward/criteria"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
        if send_to_voicemail_enabled is not None:
            body["sendToVoicemailEnabled"] = send_to_voicemail_enabled
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
        if forward_enabled is not None:
            body["forwardEnabled"] = forward_enabled
        _missing = [f for f in ['forwardToPhoneNumber', 'sendToVoicemailEnabled', 'callsFrom'] if f not in body or body[f] is None]
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



@app.command("show-criteria-selective-forward", short_help="Get a Criteria for the User’s Selective Call Forwarding Service.")
def show_criteria_selective_forward(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Criteria for the User’s Selective Call Forwarding Service.\n\n\b\nExample: wxcli user-settings show-criteria-selective-forward PERSON_ID ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_FORWARD = '{"forwardToPhoneNumber":"...","sendToVoicemailEnabled":true,"callsFrom":"ANY_PHONE_NUMBER","scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"forwardEnabled":true}'

@app.command("update-criteria-selective-forward", short_help="Modify a Criteria for the User’s Selective Call Forwarding Service.")
def update_criteria_selective_forward(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="Number to which calls needs to be forwarded."),
    send_to_voicemail_enabled: bool = typer.Option(None, "--send-to-voicemail-enabled/--no-send-to-voicemail-enabled", help="Boolean flag to enable/disable sending calls to voicemail."),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    forward_enabled: bool = typer.Option(None, "--forward-enabled/--no-forward-enabled", help="Boolean flag to enable/disable selective call forwarding."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Criteria for the User’s Selective Call Forwarding Service.\n\n\b\nExample: wxcli user-settings update-criteria-selective-forward PERSON_ID ID --forward-to-phone-number FORWARD_TO_PHONE_NUMBER --send-to-voicemail-enabled --calls-from ANY_PHONE_NUMBER\n\n\b\nExample --json-body: '{"forwardToPhoneNumber":"...","sendToVoicemailEnabled":true,"callsFrom":"ANY_PHONE_NUMBER","scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"forwardEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_FORWARD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
        if send_to_voicemail_enabled is not None:
            body["sendToVoicemailEnabled"] = send_to_voicemail_enabled
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
        if forward_enabled is not None:
            body["forwardEnabled"] = forward_enabled
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
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-selective-forward", short_help="Delete a Criteria From the User’s Selective Call Forwarding Service.")
def delete_criteria_selective_forward(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Criteria From the User’s Selective Call Forwarding Service.\n\n\b\nExample: wxcli user-settings delete-criteria-selective-forward PERSON_ID ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/selectiveForward/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-available-members-applications-1", short_help="Search Shared-Line Appearance Members New.")
def list_available_members_applications_1(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    order: str = typer.Option(None, "--order", help="Order the Route Lists according to number, ascending or descending."),
    location: str = typer.Option(None, "--location", help="Location ID for the user."),
    name: str = typer.Option(None, "--name", help="Search for users with names that match the query."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for users with numbers that match the query."),
    extension: str = typer.Option(None, "--extension", help="Search for users with extensions that match the query."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Shared-Line Appearance Members New.\n\n\b\nExample: wxcli user-settings list-available-members-applications-1 PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/availableMembers"
    params = {}
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



@app.command("show-count", short_help="Get Count of Shared-Line Appearance Members.")
def show_count(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    location_id: str = typer.Option(None, "--location-id", help="Location ID for the person."),
    member_name: str = typer.Option(None, "--member-name", help="Search for people with names that match the query."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for people with numbers that match the query."),
    extension: str = typer.Option(None, "--extension", help="Search for people with extensions that match the query."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Count of Shared-Line Appearance Members.\n\n\b\nExample: wxcli user-settings show-count PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/availableMembers/count"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-members-applications-1", short_help="Get Shared-Line Appearance Members New.")
def list_members_applications_1(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Shared-Line Appearance Members New.\n\n\b\nExample: wxcli user-settings list-members-applications-1 PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/members"
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
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE_MEMBERS_APPLICATIONS_1 = '{"members":[{"id":"...","port":0,"primaryOwner":"...","lineType":"PRIMARY","lineWeight":0,"allowCallDeclineEnabled":true,"lineLabel":"..."}]}'

@app.command("update-members-applications-1", short_help="Put Shared-Line Appearance Members New.")
def update_members_applications_1(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Put Shared-Line Appearance Members New.\n\n\b\nExample: wxcli user-settings update-members-applications-1 PERSON_ID\n\n\b\nExample --json-body: '{"members":[{"id":"...","port":0,"primaryOwner":"...","lineType":"PRIMARY","lineWeight":0,"allowCallDeclineEnabled":true,"lineLabel":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MEMBERS_APPLICATIONS_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/applications/members"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-call-captions", short_help="Get the user call captions settings.")
def show_call_captions(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the user call captions settings.\n\n\b\nExample: wxcli user-settings show-call-captions PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/callCaptions"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_CAPTIONS = '{"userClosedCaptionsEnabled":true,"userTranscriptsEnabled":true,"useLocationSettingsEnabled":true}'

@app.command("update-call-captions", short_help="Update the user call captions settings.")
def update_call_captions(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    user_closed_captions_enabled: bool = typer.Option(None, "--user-closed-captions-enabled/--no-user-closed-captions-enabled", help="Enable or disable user-level closed captions."),
    user_transcripts_enabled: bool = typer.Option(None, "--user-transcripts-enabled/--no-user-transcripts-enabled", help="Enable or disable user-level transcripts."),
    use_location_settings_enabled: bool = typer.Option(None, "--use-location-settings-enabled/--no-use-location-settings-enabled", help="If `useLocationSettingsEnabled` is `true`, location settings will control the user's closed captions and transcripts. Otherwise, user-level settings are used."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the user call captions settings.\n\n\b\nExample: wxcli user-settings update-call-captions PERSON_ID\n\n\b\nExample --json-body: '{"userClosedCaptionsEnabled":true,"userTranscriptsEnabled":true,"useLocationSettingsEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_CAPTIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/callCaptions"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if user_closed_captions_enabled is not None:
            body["userClosedCaptionsEnabled"] = user_closed_captions_enabled
        if user_transcripts_enabled is not None:
            body["userTranscriptsEnabled"] = user_transcripts_enabled
        if use_location_settings_enabled is not None:
            body["useLocationSettingsEnabled"] = use_location_settings_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-call-filtering", short_help="Get Person Executive Call Filtering Settings.")
def list_call_filtering(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Call Filtering Settings.\n\n\b\nExample: wxcli user-settings list-call-filtering PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Filter Name', 'filterName'), ('Source', 'source'), ('Activation Enabled', 'activationEnabled'), ('Filter Enabled', 'filterEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_CALL_FILTERING = '{"enabled":true,"filterType":"CUSTOM_CALL_FILTERS","criteriaActivation":[{"id":"...","activationEnabled":true}]}'

@app.command("update-call-filtering", short_help="Modify Person Executive Call Filtering Settings.")
def update_call_filtering(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Set to `true` to enable executive call filtering or `false` to disable it."),
    filter_type: str = typer.Option(None, "--filter-type", help="Choices: CUSTOM_CALL_FILTERS, ALL_CALLS, ALL_INTERNAL_CALLS, ALL_EXTERNAL_CALLS"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Call Filtering Settings.\n\n\b\nExample: wxcli user-settings update-call-filtering PERSON_ID\n\n\b\nExample --json-body: '{"enabled":true,"filterType":"CUSTOM_CALL_FILTERS","criteriaActivation":[{"id":"...","activationEnabled":true}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_FILTERING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if filter_type is not None:
            body["filterType"] = filter_type
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-criteria-call-filtering", short_help="Get Person Executive Call Filtering Criteria Settings.")
def show_criteria_call_filtering(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Call Filtering Criteria Settings.\n\n\b\nExample: wxcli user-settings show-criteria-call-filtering PERSON_ID ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_CALL_FILTERING = '{"scheduleName":"...","scheduleType":"holidays","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"filterEnabled":true,"callsToNumbers":[{"type":"PRIMARY","phoneNumber":"..."}]}'

@app.command("update-criteria-call-filtering", short_help="Modify Person Executive Call Filtering Criteria Settings.")
def update_criteria_call_filtering(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule associated with this criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: holidays, businessHours"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Set to enable or disable the criteria for anonymous callers."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Set to enable or disable the criteria for unavailable callers."),
    filter_enabled: bool = typer.Option(None, "--filter-enabled/--no-filter-enabled", help="Controls the action when this criteria matches a call. When `true`, matching calls are filtered and will alert the executive's assistants. When `false`, matching calls are not filtered and will not alert the executive's assistants. Criteria with `filterEnabled` as `false` take precedence over other..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Call Filtering Criteria Settings.\n\n\b\nExample: wxcli user-settings update-criteria-call-filtering PERSON_ID ID\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"holidays","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"filterEnabled":true,"callsToNumbers":[{"type":"PRIMARY","phoneNumber":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_CALL_FILTERING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-call-filtering", short_help="Delete Person Executive Call Filtering Criteria.")
def delete_criteria_call_filtering(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Person Executive Call Filtering Criteria.\n\n\b\nExample: wxcli user-settings delete-criteria-call-filtering PERSON_ID ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_CALL_FILTERING = '{"filterName":"...","callsFrom":"ANY_PHONE_NUMBER","filterEnabled":true,"scheduleName":"...","scheduleType":"holidays","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"callsToNumbers":[{"type":"PRIMARY","phoneNumber":"..."}]}'

@app.command("create-criteria-call-filtering", short_help="Add Person Executive Call Filtering Criteria.")
def create_criteria_call_filtering(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    filter_name: str = typer.Option(None, "--filter-name", help="(required) Name of the criteria."),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule associated with this criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: holidays, businessHours"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Set to enable or disable the criteria for anonymous callers."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Set to enable or disable the criteria for unavailable callers."),
    filter_enabled: bool = typer.Option(None, "--filter-enabled/--no-filter-enabled", help="(required) Controls the action when this criteria matches a call. When `true`, matching calls are filtered and will alert the executive's assistants. When `false`, matching calls are not filtered and will not alert the executive's assistants. Criteria with `filterEnabled` as `false` take precedence over other..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add Person Executive Call Filtering Criteria.\n\n\b\nExample: wxcli user-settings create-criteria-call-filtering PERSON_ID --filter-name FILTER_NAME --calls-from ANY_PHONE_NUMBER --filter-enabled\n\n\b\nExample --json-body: '{"filterName":"...","callsFrom":"ANY_PHONE_NUMBER","filterEnabled":true,"scheduleName":"...","scheduleType":"holidays","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"callsToNumbers":[{"type":"PRIMARY","phoneNumber":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_CALL_FILTERING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/callFiltering/criteria"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        _missing = [f for f in ['filterName', 'callsFrom', 'filterEnabled'] if f not in body or body[f] is None]
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



@app.command("show-alert", short_help="Get Person Executive Alert Settings.")
def show_alert(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Alert Settings.\n\n\b\nExample: wxcli user-settings show-alert PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/alert"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ALERT = '{"alertingMode":"SEQUENTIAL","nextAssistantNumberOfRings":0,"rolloverEnabled":true,"rolloverAction":"VOICE_MESSAGING","rolloverForwardToPhoneNumber":"...","rolloverWaitTimeInSecs":0,"clidNameMode":"EXECUTIVE_ORIGINATOR","customCLIDName":"...","customCLIDNameInUnicode":"...","clidPhoneNumberMode":"EXECUTIVE","customCLIDPhoneNumber":"..."}'

@app.command("update-alert", short_help="Modify Person Executive Alert Settings.")
def update_alert(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    alerting_mode: str = typer.Option(None, "--alerting-mode", help="Choices: SEQUENTIAL, SIMULTANEOUS"),
    next_assistant_number_of_rings: str = typer.Option(None, "--next-assistant-number-of-rings", help="Number of rings before alerting the next assistant when `alertingMode` is `SEQUENTIAL`."),
    rollover_enabled: bool = typer.Option(None, "--rollover-enabled/--no-rollover-enabled", help="Controls whether the rollover timer (`rolloverWaitTimeInSecs`) is enabled. When set to `true`, rollover will trigger after the timer expires, even if assistants are still available. When `false`, rollover only occurs when no assistants remain."),
    rollover_action: str = typer.Option(None, "--rollover-action", help="Choices: VOICE_MESSAGING, NO_ANSWER_PROCESSING, FORWARD"),
    rollover_forward_to_phone_number: str = typer.Option(None, "--rollover-forward-to-phone-number", help="Phone number to forward calls to when rollover action is set to `FORWARD`."),
    rollover_wait_time_in_secs: str = typer.Option(None, "--rollover-wait-time-in-secs", help="Time in seconds to wait before applying the rollover action when `rolloverEnabled` is `true`."),
    clid_name_mode: str = typer.Option(None, "--clid-name-mode", help="Choices: EXECUTIVE_ORIGINATOR, ORIGINATOR_EXECUTIVE, EXECUTIVE, ORIGINATOR, CUSTOM"),
    custom_clid_name: str = typer.Option(None, "--custom-clid-name", help="Custom caller ID name to display when `clidNameMode` is set to `CUSTOM` (deprecated)."),
    custom_clid_name_in_unicode: str = typer.Option(None, "--custom-clid-name-in-unicode", help="Unicode Custom caller ID name to display when `clidNameMode` is set to `CUSTOM`."),
    clid_phone_number_mode: str = typer.Option(None, "--clid-phone-number-mode", help="Choices: EXECUTIVE, ORIGINATOR, CUSTOM"),
    custom_clid_phone_number: str = typer.Option(None, "--custom-clid-phone-number", help="Custom caller ID phone number to display on assistant's phone when `clidPhoneNumberMode` is set to `CUSTOM`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Alert Settings.\n\n\b\nExample: wxcli user-settings update-alert PERSON_ID\n\n\b\nExample --json-body: '{"alertingMode":"SEQUENTIAL","nextAssistantNumberOfRings":0,"rolloverEnabled":true,"rolloverAction":"VOICE_MESSAGING","rolloverForwardToPhoneNumber":"...","rolloverWaitTimeInSecs":0,"clidNameMode":"EXECUTIVE_ORIGINATOR","customCLIDName":"...","customCLIDNameInUnicode":"...","clidPhoneNumberMode":"EXECUTIVE","customCLIDPhoneNumber":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ALERT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/alert"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-assigned-assistants", short_help="Get Person Executive Assigned Assistants.")
def list_assigned_assistants(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Assigned Assistants.\n\n\b\nExample: wxcli user-settings list-assigned-assistants PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/assignedAssistants"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("assistants", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Direct Number', 'directNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE_ASSIGNED_ASSISTANTS = '{"assistantIds":["..."]}'

@app.command("update-assigned-assistants", short_help="Modify Person Executive Assigned Assistants.")
def update_assigned_assistants(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Assigned Assistants.\n\n\b\nExample: wxcli user-settings update-assigned-assistants PERSON_ID\n\n\b\nExample --json-body: '{"assistantIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ASSIGNED_ASSISTANTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/assignedAssistants"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-available-assistants", short_help="Get Person Executive Available Assistants.")
def list_available_assistants(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    name: str = typer.Option(None, "--name", help="Only return people with the matching name (person's first and last name combination)."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return people with the matching phone number or extension."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Available Assistants.\n\n\b\nExample: wxcli user-settings list-available-assistants PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/availableAssistants"
    params = {}
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("assistants", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Direct Number', 'directNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-assistant", short_help="Get Person Executive Assistant Settings.")
def list_assistant(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Assistant Settings.\n\n\b\nExample: wxcli user-settings list-assistant PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/assistant"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("executives", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Direct Number', 'directNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE_ASSISTANT = '{"forwardFilteredCallsEnabled":true,"forwardToPhoneNumber":"...","executives":[{"personId":"...","optInEnabled":true}]}'

@app.command("update-assistant", short_help="Modify Person Executive Assistant Settings.")
def update_assistant(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    forward_filtered_calls_enabled: bool = typer.Option(None, "--forward-filtered-calls-enabled/--no-forward-filtered-calls-enabled", help="If `true`, filtered calls to assistant are forwarded to the `forwardToPhoneNumber`."),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="Phone number to forward the filtered calls to. Mandatory if `forwardFilteredCallsEnabled` is set to true."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Assistant Settings.\n\n\b\nExample: wxcli user-settings update-assistant PERSON_ID\n\n\b\nExample --json-body: '{"forwardFilteredCallsEnabled":true,"forwardToPhoneNumber":"...","executives":[{"personId":"...","optInEnabled":true}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ASSISTANT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/assistant"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if forward_filtered_calls_enabled is not None:
            body["forwardFilteredCallsEnabled"] = forward_filtered_calls_enabled
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-screening", short_help="Get Person Executive Screening Settings.")
def show_screening(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Executive Screening Settings.\n\n\b\nExample: wxcli user-settings show-screening PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/screening"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SCREENING = '{"enabled":true,"alertType":"SILENT","alertAnywhereLocationEnabled":true,"alertMobilityLocationEnabled":true,"alertSharedCallAppearanceLocationEnabled":true}'

@app.command("update-screening", short_help="Modify Person Executive Screening Settings.")
def update_screening(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Set to enable or disable executive screening."),
    alert_type: str = typer.Option(None, "--alert-type", help="Choices: SILENT, RING_SPLASH"),
    alert_anywhere_location_enabled: bool = typer.Option(None, "--alert-anywhere-location-enabled/--no-alert-anywhere-location-enabled", help="Indicates if alerts are enabled for Single Number Reach locations."),
    alert_mobility_location_enabled: bool = typer.Option(None, "--alert-mobility-location-enabled/--no-alert-mobility-location-enabled", help="Indicates if alerts are enabled for Webex Go locations."),
    alert_shared_call_appearance_location_enabled: bool = typer.Option(None, "--alert-shared-call-appearance-location-enabled/--no-alert-shared-call-appearance-location-enabled", help="Indicates if alerts are enabled for Shared Call Appearance locations."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Person Executive Screening Settings.\n\n\b\nExample: wxcli user-settings update-screening PERSON_ID\n\n\b\nExample --json-body: '{"enabled":true,"alertType":"SILENT","alertAnywhereLocationEnabled":true,"alertMobilityLocationEnabled":true,"alertSharedCallAppearanceLocationEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SCREENING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/executive/screening"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-people", short_help="Get Timezone and Announcement Language Settings of a Person.")
def show_people(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Timezone and Announcement Language Settings of a Person.\n\n\b\nExample: wxcli user-settings show-people PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_PEOPLE = '{"announcementLanguage":"...","timeZone":"..."}'

@app.command("update-people", short_help="Update Timezone and Announcement Language Settings of a Person.")
def update_people(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    announcement_language: str = typer.Option(None, "--announcement-language", help="Person's phone announcement language."),
    time_zone: str = typer.Option(None, "--time-zone", help="Timezone associated with the person for calling configuration. Refer to the Get Country Configuration API to retrieve the list of available timezones for a specific country."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Timezone and Announcement Language Settings of a Person.\n\n\b\nExample: wxcli user-settings update-people PERSON_ID\n\n\b\nExample --json-body: '{"announcementLanguage":"...","timeZone":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PEOPLE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if announcement_language is not None:
            body["announcementLanguage"] = announcement_language
        if time_zone is not None:
            body["timeZone"] = time_zone
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-countries", short_help="Get Country Calling Configuration.")
def show_countries(
    country_code: str = typer.Argument(help="countryCode"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Country Calling Configuration.\n\n\b\nExample: wxcli user-settings show-countries COUNTRY_CODE"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/countries/{country_code}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-anonymous-call-reject", short_help="Get Anonymous Call Rejection Settings for a Person.")
def show_anonymous_call_reject(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Anonymous Call Rejection Settings for a Person.\n\n\b\nExample: wxcli user-settings show-anonymous-call-reject PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/anonymousCallReject"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ANONYMOUS_CALL_REJECT = '{"enabled":true}'

@app.command("update-anonymous-call-reject", short_help="Update Anonymous Call Rejection Settings for a Person.")
def update_anonymous_call_reject(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable or disable Anonymous Call Rejection. When set to true, incoming calls from callers who have blocked their caller ID will be automatically rejected."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Anonymous Call Rejection Settings for a Person.\n\n\b\nExample: wxcli user-settings update-anonymous-call-reject PERSON_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ANONYMOUS_CALL_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/anonymousCallReject"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-services", short_help="List Enabled Calling Services for a Person.")
def list_services(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Enabled Calling Services for a Person.\n\n\b\nExample: wxcli user-settings list-services PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/services"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("services", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-simultaneous-ring", short_help="Retrieve Simultaneous Ring Settings for a Person.")
def list_simultaneous_ring(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Simultaneous Ring Settings for a Person.\n\n\b\nExample: wxcli user-settings list-simultaneous-ring PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Answer Confirmation Enabled', 'answerConfirmationEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SIMULTANEOUS_RING = '{"enabled":true,"doNotRingIfOnCallEnabled":true,"criteriasEnabled":true,"phoneNumbers":[{"phoneNumber":"...","answerConfirmationEnabled":true}]}'

@app.command("update-simultaneous-ring", short_help="Modify Simultaneous Ring Settings for a Person.")
def update_simultaneous_ring(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="When set to `true`, simultaneous ring is enabled for this person."),
    do_not_ring_if_on_call_enabled: bool = typer.Option(None, "--do-not-ring-if-on-call-enabled/--no-do-not-ring-if-on-call-enabled", help="When set to `true`, the configured phone numbers won't ring when you are on a call."),
    criterias_enabled: bool = typer.Option(None, "--criterias-enabled/--no-criterias-enabled", help="When `true`, enables the selected schedule for simultaneous ring."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Simultaneous Ring Settings for a Person.\n\n\b\nExample: wxcli user-settings update-simultaneous-ring PERSON_ID\n\n\b\nExample --json-body: '{"enabled":true,"doNotRingIfOnCallEnabled":true,"criteriasEnabled":true,"phoneNumbers":[{"phoneNumber":"...","answerConfirmationEnabled":true}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SIMULTANEOUS_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if do_not_ring_if_on_call_enabled is not None:
            body["doNotRingIfOnCallEnabled"] = do_not_ring_if_on_call_enabled
        if criterias_enabled is not None:
            body["criteriasEnabled"] = criterias_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_SIMULTANEOUS_RING = '{"callsFrom":"ANY_PHONE_NUMBER","ringEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"LOCATION","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("create-criteria-simultaneous-ring", short_help="Create Simultaneous Ring Criteria for a Person.")
def create_criteria_simultaneous_ring(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule which determines when the simultaneous ring is in effect."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: LOCATION, PEOPLE"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, the criteria applies to calls from anonymous callers. Value for this attribute is required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, the criteria applies to calls from unavailable callers. Value for this attribute is required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="(required) When set to `true` simultaneous ringing is enabled for calls that meet this criteria. Criteria with `ringEnabled` set to `false` take priority."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Simultaneous Ring Criteria for a Person.\n\n\b\nExample: wxcli user-settings create-criteria-simultaneous-ring PERSON_ID --calls-from ANY_PHONE_NUMBER --ring-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","ringEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"LOCATION","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SIMULTANEOUS_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing/criteria"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        if ring_enabled is not None:
            body["ringEnabled"] = ring_enabled
        _missing = [f for f in ['callsFrom', 'ringEnabled'] if f not in body or body[f] is None]
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



@app.command("show-criteria-simultaneous-ring", short_help="Retrieve Simultaneous Ring Criteria for a Person.")
def show_criteria_simultaneous_ring(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Simultaneous Ring Criteria for a Person.\n\n\b\nExample: wxcli user-settings show-criteria-simultaneous-ring PERSON_ID ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SIMULTANEOUS_RING = '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"LOCATION","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'

@app.command("update-criteria-simultaneous-ring", short_help="Modify Simultaneous Ring Criteria for a Person.")
def update_criteria_simultaneous_ring(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule which determines when the simultaneous ring is in effect."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: LOCATION, PEOPLE"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, the criteria applies to calls from anonymous callers. Value for this attribute is required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, the criteria applies to calls from unavailable callers. Value for this attribute is required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="When set to `true` simultaneous ringing is enabled for calls that meet this criteria. Criteria with `ringEnabled` set to `false` take priority."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Simultaneous Ring Criteria for a Person.\n\n\b\nExample: wxcli user-settings update-criteria-simultaneous-ring PERSON_ID ID\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"LOCATION","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SIMULTANEOUS_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        if ring_enabled is not None:
            body["ringEnabled"] = ring_enabled
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
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-simultaneous-ring", short_help="Delete Simultaneous Ring Criteria for a Person.")
def delete_criteria_simultaneous_ring(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Simultaneous Ring Criteria for a Person.\n\n\b\nExample: wxcli user-settings delete-criteria-simultaneous-ring PERSON_ID ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-available-members-hot-desking", short_help="Search Available Hot Desking Members.")
def list_available_members_hot_desking(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    location_id: str = typer.Option(None, "--location-id", help="Return only available members in this location."),
    member_name: str = typer.Option(None, "--member-name", help="Search for available members by name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for available members by phone number."),
    extension: str = typer.Option(None, "--extension", help="Search for available members by extension."),
    order: str = typer.Option(None, "--order", help="Sort order for the available member list. Multiple order values may be provided."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Available Hot Desking Members.\n\n\b\nExample: wxcli user-settings list-available-members-hot-desking PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/availableMembers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="members"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-members-hot-desking", short_help="Get Hot Desking Members.")
def list_members_hot_desking(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hot Desking Members.\n\n\b\nExample: wxcli user-settings list-members-hot-desking PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/members"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE_MEMBERS_HOT_DESKING = '{"members":[{"id":"...","port":0,"primaryOwner":true,"lineType":"HOTDESKING_GUEST","lineWeight":0,"t38FaxCompressionEnabled":true,"hotlineEnabled":true,"hotlineDestination":"...","allowCallDeclineEnabled":true,"memberType":"USER"}]}'

@app.command("update-members-hot-desking", short_help="Update Hot Desking Members.")
def update_members_hot_desking(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Hot Desking Members.\n\n\b\nExample: wxcli user-settings update-members-hot-desking PERSON_ID --json-body '{"members":[{"id":"...","port":0,"primaryOwner":true,"lineType":"HOTDESKING_GUEST","lineWeight":0}]}'\n\n\b\nExample --json-body: '{"members":[{"id":"...","port":0,"primaryOwner":true,"lineType":"HOTDESKING_GUEST","lineWeight":0,"t38FaxCompressionEnabled":true,"hotlineEnabled":true,"hotlineDestination":"...","allowCallDeclineEnabled":true,"memberType":"USER"}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MEMBERS_HOT_DESKING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/members"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("list-outbound-billing-plan", short_help="Retrieve a Person's Outbound Billing Plan.")
def list_outbound_billing_plan(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a Person's Outbound Billing Plan.\n\n\b\nExample: wxcli user-settings list-outbound-billing-plan PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outboundBillingPlan"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-outbound-billing-plan", short_help="Modify a Person's Outbound Billing Plan.")
def update_outbound_billing_plan(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Person's Outbound Billing Plan.\n\n\b\nExample: wxcli user-settings update-outbound-billing-plan PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/outboundBillingPlan"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)


