import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling call-settings-for-me-phase-5.")


@app.command("show", short_help="Get Personal Assistant Settings.")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Personal Assistant Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/personalAssistant"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"enabled":true,"presence":"BUSINESS_TRIP","untilDateTime":"...","transferEnabled":true,"transferNumber":"...","alerting":"ALERT_ME_FIRST","alertMeFirstNumberOfRings":0}'

@app.command("update", short_help="Update Personal Assistant Settings.")
def update(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable/Disable the personal assistant feature."),
    presence: str = typer.Option(None, "--presence", help="Choices: BUSINESS_TRIP, GONE_FOR_THE_DAY, LUNCH, MEETING, OUT_OF_OFFICE, TEMPORARILY_OUT, TRAINING, UNAVAILABLE, VACATION"),
    until_date_time: str = typer.Option(None, "--until-date-time", help="Date and time until which the personal assistant is active (ISO 8601 format)."),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help="Enable/Disable call transfer when personal assistant is active."),
    transfer_number: str = typer.Option(None, "--transfer-number", help="Phone number to transfer calls to when transfer is enabled."),
    alerting: str = typer.Option(None, "--alerting", help="Choices: ALERT_ME_FIRST, PLAY_RING_REMINDER, NONE"),
    alert_me_first_number_of_rings: str = typer.Option(None, "--alert-me-first-number-of-rings", help="Number of rings before transferring the call when alerting is set to ALERT_ME_FIRST."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Personal Assistant Settings.\n\n\b\nExample: wxcli call-settings-for-me-phase-5 update --enabled\n\n\b\nExample --json-body: '{"enabled":true,"presence":"BUSINESS_TRIP","untilDateTime":"...","transferEnabled":true,"transferNumber":"...","alerting":"ALERT_ME_FIRST","alertMeFirstNumberOfRings":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/personalAssistant"
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-rules", short_help="Get Person's Voicemail Rules.")
def show_rules(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person's Voicemail Rules."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/voicemail/rules"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_PIN = '{"passcode":"..."}'

@app.command("update-pin", short_help="Update Voicemail PIN.")
def update_pin(
    passcode: str = typer.Option(None, "--passcode", help="Person voicemail PIN. The PIN must comply with the passcode rules defined for the organization."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voicemail PIN.\n\n\b\nExample: wxcli call-settings-for-me-phase-5 update-pin --passcode PASSCODE\n\n\b\nExample --json-body: '{"passcode":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PIN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/voicemail/pin"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if passcode is not None:
            body["passcode"] = passcode
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-guest", short_help="Get Hoteling Guest Settings.")
def show_guest(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hoteling Guest Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/hoteling/guest"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_GUEST = '{"enabled":true,"associationLimitEnabled":true,"associationLimitHours":0,"hostId":"..."}'

@app.command("update-guest", short_help="Update Hoteling Guest Settings.")
def update_guest(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable/Disable hoteling guest functionality for the person. When enabled, the person can associate themselves with a hoteling host device."),
    association_limit_enabled: bool = typer.Option(None, "--association-limit-enabled/--no-association-limit-enabled", help="When enabled, the person's hoteling guest association will be automatically removed after the specified time period."),
    association_limit_hours: str = typer.Option(None, "--association-limit-hours", help="Time limit in hours for the hoteling guest association (1-999). Applicable when associationLimitEnabled is true."),
    host_id: str = typer.Option(None, "--host-id", help="Unique identifier of the hoteling host person or workspace to associate with. Required when enabling hoteling guest functionality."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Hoteling Guest Settings.\n\n\b\nExample: wxcli call-settings-for-me-phase-5 update-guest --enabled\n\n\b\nExample --json-body: '{"enabled":true,"associationLimitEnabled":true,"associationLimitHours":0,"hostId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_GUEST), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/hoteling/guest"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if association_limit_enabled is not None:
            body["associationLimitEnabled"] = association_limit_enabled
        if association_limit_hours is not None:
            body["associationLimitHours"] = association_limit_hours
        if host_id is not None:
            body["hostId"] = host_id
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("list", short_help="Get Available Hoteling Hosts.")
def cmd_list(
    name: str = typer.Option(None, "--name", help="Filter hosts by name (first name or last name). Partial match is supported."),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter hosts by phone number. Partial match is supported."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Hoteling Hosts."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/hoteling/availableHosts"
    params = {}
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
    items = result.get("hosts", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Host ID', 'hostId'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)


