import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling call-settings-for-me-phase-5.")


@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Personal Assistant Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/personalAssistant"
    try:
        result = api.session.rest_get(url)
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



@app.command("update")
def update(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable/Disable the personal assistant feature."),
    presence: str = typer.Option(None, "--presence", help="Presence status that triggers the personal assistant. (use --help for choices)"),
    until_date_time: str = typer.Option(None, "--until-date-time", help="Date and time until which the personal assistant is active ("),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help="Enable/Disable call transfer when personal assistant is acti"),
    transfer_number: str = typer.Option(None, "--transfer-number", help="Phone number to transfer calls to when transfer is enabled."),
    alerting: str = typer.Option(None, "--alerting", help="Choices: ALERT_ME_FIRST, PLAY_RING_REMINDER, NONE"),
    alert_me_first_number_of_rings: str = typer.Option(None, "--alert-me-first-number-of-rings", help="Number of rings before transferring the call when alerting i"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Personal Assistant Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/personalAssistant"
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
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-rules")
def show_rules(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person's Voicemail Rules."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/voicemail/rules"
    try:
        result = api.session.rest_get(url)
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



@app.command("update-pin")
def update_pin(
    passcode: str = typer.Option(None, "--passcode", help="Person voicemail PIN. The PIN must comply with the passcode"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voicemail PIN."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/voicemail/pin"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if passcode is not None:
            body["passcode"] = passcode
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-guest")
def show_guest(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hoteling Guest Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/hoteling/guest"
    try:
        result = api.session.rest_get(url)
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



@app.command("update-guest")
def update_guest(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable/Disable hoteling guest functionality for the person."),
    association_limit_enabled: bool = typer.Option(None, "--association-limit-enabled/--no-association-limit-enabled", help="When enabled, the person's hoteling guest association will b"),
    association_limit_hours: str = typer.Option(None, "--association-limit-hours", help="Time limit in hours for the hoteling guest association (1-99"),
    host_id: str = typer.Option(None, "--host-id", help="Unique identifier of the hoteling host person or workspace t"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Hoteling Guest Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/hoteling/guest"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    name: str = typer.Option(None, "--name", help="Filter hosts by name (first name or last name). Partial matc"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter hosts by phone number. Partial match is supported."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("hosts", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


