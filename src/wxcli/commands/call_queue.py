import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling call-queue.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Returns the list of call queues in this location."),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Returns only the call queues matching the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the call queues matching the given primary phon"),
    department_id: str = typer.Option(None, "--department-id", help="Returns only call queues matching the given department ID."),
    department_name: str = typer.Option(None, "--department-name", help="Returns only call queues matching the given department name."),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of call queues with Customer Experienc"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Queues with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if department_id is not None:
        params["departmentId"] = department_id
    if department_name is not None:
        params["departmentName"] = department_name
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
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
    items = result.get("queues", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(..., "--name", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    language_code: str = typer.Option(None, "--language-code", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    time_zone: str = typer.Option(None, "--time-zone", help=""),
    calling_line_id_policy: str = typer.Option(None, "--calling-line-id-policy", help="e.g. CUSTOM"),
    calling_line_id_phone_number: str = typer.Option(None, "--calling-line-id-phone-number", help=""),
    allow_agent_join_enabled: bool = typer.Option(None, "--allow-agent-join-enabled/--no-allow-agent-join-enabled", help=""),
    phone_number_for_outgoing_calls_enabled: bool = typer.Option(None, "--phone-number-for-outgoing-calls-enabled/--no-phone-number-for-outgoing-calls-enabled", help=""),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Call Queue with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        body.setdefault('callPolicies', {'routingType': 'PRIORITY_BASED', 'policy': 'CIRCULAR'})
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if language_code is not None:
            body["languageCode"] = language_code
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if time_zone is not None:
            body["timeZone"] = time_zone
        if calling_line_id_policy is not None:
            body["callingLineIdPolicy"] = calling_line_id_policy
        if calling_line_id_phone_number is not None:
            body["callingLineIdPhoneNumber"] = calling_line_id_phone_number
        if allow_agent_join_enabled is not None:
            body["allowAgentJoinEnabled"] = allow_agent_join_enabled
        if phone_number_for_outgoing_calls_enabled is not None:
            body["phoneNumberForOutgoingCallsEnabled"] = phone_number_for_outgoing_calls_enabled
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
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



@app.command("delete")
def delete(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Queue."""
    if not force:
        typer.confirm(f"Delete {queue_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {queue_id}")



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}"
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
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    name: str = typer.Option(None, "--name", help=""),
    language_code: str = typer.Option(None, "--language-code", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    time_zone: str = typer.Option(None, "--time-zone", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    calling_line_id_policy: str = typer.Option(None, "--calling-line-id-policy", help="e.g. CUSTOM"),
    calling_line_id_phone_number: str = typer.Option(None, "--calling-line-id-phone-number", help=""),
    allow_call_waiting_for_agents_enabled: bool = typer.Option(None, "--allow-call-waiting-for-agents-enabled/--no-allow-call-waiting-for-agents-enabled", help=""),
    allow_agent_join_enabled: bool = typer.Option(None, "--allow-agent-join-enabled/--no-allow-agent-join-enabled", help=""),
    phone_number_for_outgoing_calls_enabled: bool = typer.Option(None, "--phone-number-for-outgoing-calls-enabled/--no-phone-number-for-outgoing-calls-enabled", help=""),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if name is not None:
            body["name"] = name
        if language_code is not None:
            body["languageCode"] = language_code
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if time_zone is not None:
            body["timeZone"] = time_zone
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if calling_line_id_policy is not None:
            body["callingLineIdPolicy"] = calling_line_id_policy
        if calling_line_id_phone_number is not None:
            body["callingLineIdPhoneNumber"] = calling_line_id_phone_number
        if allow_call_waiting_for_agents_enabled is not None:
            body["allowCallWaitingForAgentsEnabled"] = allow_call_waiting_for_agents_enabled
        if allow_agent_join_enabled is not None:
            body["allowAgentJoinEnabled"] = allow_agent_join_enabled
        if phone_number_for_outgoing_calls_enabled is not None:
            body["phoneNumberForOutgoingCallsEnabled"] = phone_number_for_outgoing_calls_enabled
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
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



@app.command("list-announcements")
def list_announcements(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Queue Announcement Files."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/announcements"
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
    items = result.get("announcements", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("delete-announcements")
def delete_announcements(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    file_name: str = typer.Argument(help="fileName"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Queue Announcement File."""
    if not force:
        typer.confirm(f"Delete {file_name}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/announcements/{file_name}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {file_name}")



@app.command("show-call-forwarding")
def show_call_forwarding(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Forwarding Settings for a Call Queue."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding"
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
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Forwarding Settings for a Call Queue."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding"
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



@app.command("create-selective-rules")
def create_selective_rules(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    name: str = typer.Option(..., "--name", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help=""),
    business_schedule: str = typer.Option(None, "--business-schedule", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Selective Call Forwarding Rule for a Call Queue."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if enabled is not None:
            body["enabled"] = enabled
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
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



@app.command("show-selective-rules")
def show_selective_rules(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    rule_id: str = typer.Argument(help="ruleId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Forwarding Rule for a Call Queue."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules/{rule_id}"
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



@app.command("update-selective-rules")
def update_selective_rules(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    rule_id: str = typer.Argument(help="ruleId"),
    name: str = typer.Option(None, "--name", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help=""),
    business_schedule: str = typer.Option(None, "--business-schedule", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Selective Call Forwarding Rule for a Call Queue."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules/{rule_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if enabled is not None:
            body["enabled"] = enabled
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
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



@app.command("delete-selective-rules")
def delete_selective_rules(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    rule_id: str = typer.Argument(help="ruleId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Forwarding Rule for a Call Queue."""
    if not force:
        typer.confirm(f"Delete {rule_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules/{rule_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {rule_id}")



@app.command("show-holiday-service")
def show_holiday_service(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Holiday Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/holidayService"
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



@app.command("update-holiday-service")
def update_holiday_service(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    holiday_service_enabled: bool = typer.Option(None, "--holiday-service-enabled/--no-holiday-service-enabled", help=""),
    action: str = typer.Option(None, "--action", help="e.g. BUSY"),
    holiday_schedule_level: str = typer.Option(None, "--holiday-schedule-level", help="e.g. ORGANIZATION"),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help=""),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="e.g. DEFAULT"),
    holiday_schedule_name: str = typer.Option(None, "--holiday-schedule-name", help=""),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Holiday Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/holidayService"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if holiday_service_enabled is not None:
            body["holidayServiceEnabled"] = holiday_service_enabled
        if action is not None:
            body["action"] = action
        if holiday_schedule_level is not None:
            body["holidayScheduleLevel"] = holiday_schedule_level
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
        if holiday_schedule_name is not None:
            body["holidayScheduleName"] = holiday_schedule_name
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
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



@app.command("show-night-service")
def show_night_service(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Night Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/nightService"
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



@app.command("update-night-service")
def update_night_service(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    night_service_enabled: bool = typer.Option(None, "--night-service-enabled/--no-night-service-enabled", help=""),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help=""),
    announcement_mode: str = typer.Option(None, "--announcement-mode", help="e.g. MANUAL"),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="e.g. DEFAULT"),
    force_night_service_enabled: bool = typer.Option(None, "--force-night-service-enabled/--no-force-night-service-enabled", help=""),
    manual_audio_message_selection: str = typer.Option(None, "--manual-audio-message-selection", help="e.g. CUSTOM"),
    action: str = typer.Option(None, "--action", help="e.g. BUSY"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help=""),
    business_hours_name: str = typer.Option(None, "--business-hours-name", help=""),
    business_hours_level: str = typer.Option(None, "--business-hours-level", help="e.g. LOCATION"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Night Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/nightService"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if night_service_enabled is not None:
            body["nightServiceEnabled"] = night_service_enabled
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if announcement_mode is not None:
            body["announcementMode"] = announcement_mode
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
        if force_night_service_enabled is not None:
            body["forceNightServiceEnabled"] = force_night_service_enabled
        if manual_audio_message_selection is not None:
            body["manualAudioMessageSelection"] = manual_audio_message_selection
        if action is not None:
            body["action"] = action
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if business_hours_name is not None:
            body["businessHoursName"] = business_hours_name
        if business_hours_level is not None:
            body["businessHoursLevel"] = business_hours_level
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



@app.command("show-forced-forward")
def show_forced_forward(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Forced Forward."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/forcedForward"
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



@app.command("update-forced-forward")
def update_forced_forward(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    forced_forward_enabled: bool = typer.Option(None, "--forced-forward-enabled/--no-forced-forward-enabled", help=""),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help=""),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="e.g. DEFAULT"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Forced Forward service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/forcedForward"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if forced_forward_enabled is not None:
            body["forcedForwardEnabled"] = forced_forward_enabled
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
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



@app.command("show-stranded-calls")
def show_stranded_calls(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Stranded Calls."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/strandedCalls"
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



@app.command("update-stranded-calls")
def update_stranded_calls(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    action: str = typer.Option(None, "--action", help="e.g. RINGING"),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="e.g. CUSTOM"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Stranded Calls service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/strandedCalls"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if action is not None:
            body["action"] = action
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
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



@app.command("list-available-numbers")
def list_available_numbers(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Primary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/availableNumbers"
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
    items = result.get("availableNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-numbers")
def list_available_numbers(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Alternate Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/alternate/availableNumbers"
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
    items = result.get("availableNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-numbers")
def list_available_numbers(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `exten"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Call Forward Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/callForwarding/availableNumbers"
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
    items = result.get("availableNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-agents")
def list_available_agents(
    location_id: str = typer.Option(None, "--location-id", help="The location ID of the call queue. Temporary mandatory query"),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Search based on name (user first and last name combination)."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search based on number or extension."),
    order: str = typer.Option(None, "--order", help="Order the available agents according to the designated field"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Available Agents."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/availableAgents"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
    items = result.get("availableAgents", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-supervisors")
def list_supervisors(
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Only return the supervisors that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return the supervisors that match the given phone numbe"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of supervisors with Customer Experienc"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of Supervisors with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
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
    items = result.get("supervisors", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("create-supervisors")
def create_supervisors(
    id_param: str = typer.Option(None, "--id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Supervisor with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
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



@app.command("delete-supervisors")
def delete_supervisors(
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Bulk supervisors."""
    if not force:
        typer.confirm(f"Delete {item}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {item}")



@app.command("delete-supervisors")
def delete_supervisors(
    supervisor_id: str = typer.Argument(help="supervisorId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete A Supervisor."""
    if not force:
        typer.confirm(f"Delete {supervisor_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {supervisor_id}")



@app.command("show-supervisors")
def show_supervisors(
    supervisor_id: str = typer.Argument(help="supervisorId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """GET Supervisor Detail with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
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



@app.command("update-supervisors")
def update_supervisors(
    supervisor_id: str = typer.Argument(help="supervisorId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign or Unassign Agents to Supervisor with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
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



@app.command("list-available-supervisors")
def list_available_supervisors(
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Only return the supervisors that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return the supervisors that match the given phone numbe"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of available supervisors with Customer"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Supervisors with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/availableSupervisors"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
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
    items = result.get("availableSupervisors", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-agents")
def list_available_agents(
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Returns only the agents that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the agents that match the phone number, extensi"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of available agents with Customer Expe"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Agents with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/availableAgents"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
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
    items = result.get("availableAgents", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-agents")
def list_agents(
    location_id: str = typer.Option(None, "--location-id", help="Return only the call queue agents in this location."),
    queue_id: str = typer.Option(None, "--queue-id", help="Only return call queue agents with the matching queue ID."),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Returns only the list of call queue agents that match the gi"),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the list of call queue agents that match the gi"),
    join_enabled: str = typer.Option(None, "--join-enabled", help="Returns only the list of call queue agents that match the gi"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of call queues with Customer Experienc"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by call queue agent's name, in a"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Queue Agents with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if queue_id is not None:
        params["queueId"] = queue_id
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if join_enabled is not None:
        params["joinEnabled"] = join_enabled
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
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
    items = result.get("agents", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("show-agents")
def show_agents(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Agent with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/{id}"
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



@app.command("update-settings")
def update_settings(
    id: str = typer.Argument(help="id"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Agent's Settings of One or More Call Queues with Customer Experience Essentials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/{id}/settings"
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



@app.command("switch-mode-for")
def switch_mode_for(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Call Forwarding Settings for a Call Queue."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/actions/switchMode/invoke"
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


