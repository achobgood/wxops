import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling call-queue.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Returns the list of call queues in this location."),
    name: str = typer.Option(None, "--name", help="Returns only the call queues matching the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the call queues matching the given primary phon"),
    department_id: str = typer.Option(None, "--department-id", help="Returns only call queues matching the given department ID."),
    department_name: str = typer.Option(None, "--department-name", help="Returns only call queues matching the given department name."),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of call queues with Customer Assist li"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Queues with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("queues", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="queues"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Creates a Customer Assist call queue, when `true`. This requ"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the call queue."),
    phone_number: str = typer.Option(None, "--phone-number", help="Primary phone number of the call queue. Either a `phoneNumbe"),
    extension: str = typer.Option(None, "--extension", help="Primary phone extension of the call queue. Either a `phoneNu"),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name to be shown when calls are forwarded out of this"),
    last_name: str = typer.Option(None, "--last-name", help="Last name to be shown when calls are forwarded out of this c"),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone for the call queue."),
    calling_line_id_policy: str = typer.Option(None, "--calling-line-id-policy", help="Choices: DIRECT_LINE, LOCATION_NUMBER, CUSTOM"),
    calling_line_id_phone_number: str = typer.Option(None, "--calling-line-id-phone-number", help="Calling line ID Phone number which will be shown if CUSTOM i"),
    allow_agent_join_enabled: bool = typer.Option(None, "--allow-agent-join-enabled/--no-allow-agent-join-enabled", help="Whether or not to allow agents to join or unjoin a queue."),
    phone_number_for_outgoing_calls_enabled: bool = typer.Option(None, "--phone-number-for-outgoing-calls-enabled/--no-phone-number-for-outgoing-calls-enabled", help="When `true`, indicates that the agent's configuration allows"),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="The name to be used for dial by name functions. Characters o"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Call Queue with Customer Assist\n\nExample --json-body:\n  '{"name":"...","callPolicies":{"routingType":"PRIORITY_BASED","policy":"CIRCULAR","callBounce":{"callBounceEnabled":"...","callBounceMaxRings":"...","agentUnavailableEnabled":"...","alertAgentEnabled":"...","alertAgentMaxSeconds":"...","callBounceOnHoldEnabled":"...","callBounceOnHoldMaxSeconds":"..."},"distinctiveRing":{"enabled":"...","ringPattern":"..."}},"queueSettings":{"queueSize":0,"overflow":{"action":"...","greeting":"...","sendToVoicemail":"...","transferNumber":"...","overflowAfterWaitEnabled":"...","overflowAfterWaitTime":"...","playOverflowGreetingEnabled":"...","audioAnnouncementFiles":"..."},"callOfferToneEnabled":true,"resetCallStatisticsEnabled":true,"welcomeMessage":{"greeting":"...","enabled":"...","alwaysEnabled":"...","audioAnnouncementFiles":"..."},"waitMessage":{"waitMode":"...","enabled":"...","handlingTime":"...","defaultHandlingTime":"...","queuePosition":"...","highVolumeMessageEnabled":"...","estimatedWaitingTime":"...","callbackOptionEnabled":"..."},"comfortMessage":{"greeting":"...","enabled":"...","timeBetweenMessages":"...","audioAnnouncementFiles":"..."},"comfortMessageBypass":{"greeting":"...","enabled":"...","callWaitingAgeThreshold":"...","audioAnnouncementFiles":"..."}},"agents":[{"id":"...","weight":"...","skillLevel":"..."}],"phoneNumber":"...","extension":"...","languageCode":"...","firstName":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
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
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true`, to view the details of a call queue w"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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



@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not the call queue is enabled."),
    name: str = typer.Option(None, "--name", help="Unique name for the call queue."),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name to be shown when calls are forwarded out of this"),
    last_name: str = typer.Option(None, "--last-name", help="Last name to be shown when calls are forwarded out of this c"),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone for the hunt group."),
    phone_number: str = typer.Option(None, "--phone-number", help="Primary phone number of the call queue."),
    extension: str = typer.Option(None, "--extension", help="Extension of the call queue."),
    calling_line_id_policy: str = typer.Option(None, "--calling-line-id-policy", help="Choices: DIRECT_LINE, LOCATION_NUMBER, CUSTOM"),
    calling_line_id_phone_number: str = typer.Option(None, "--calling-line-id-phone-number", help="Calling line ID Phone number which will be shown if CUSTOM i"),
    allow_call_waiting_for_agents_enabled: bool = typer.Option(None, "--allow-call-waiting-for-agents-enabled/--no-allow-call-waiting-for-agents-enabled", help="Flag to indicate whether call waiting is enabled for agents."),
    allow_agent_join_enabled: bool = typer.Option(None, "--allow-agent-join-enabled/--no-allow-agent-join-enabled", help="Whether or not to allow agents to join or unjoin a queue."),
    phone_number_for_outgoing_calls_enabled: bool = typer.Option(None, "--phone-number-for-outgoing-calls-enabled/--no-phone-number-for-outgoing-calls-enabled", help="When `true`, indicates that the agent's configuration allows"),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name function"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue\n\nExample --json-body:\n  '{"queueSettings":{"queueSize":0,"overflow":{"action":"...","greeting":"...","sendToVoicemail":"...","transferNumber":"...","overflowAfterWaitEnabled":"...","overflowAfterWaitTime":"...","playOverflowGreetingEnabled":"...","audioAnnouncementFiles":"..."},"callOfferToneEnabled":true,"resetCallStatisticsEnabled":true,"welcomeMessage":{"greeting":"...","enabled":"...","alwaysEnabled":"...","audioAnnouncementFiles":"..."},"waitMessage":{"waitMode":"...","enabled":"...","handlingTime":"...","defaultHandlingTime":"...","queuePosition":"...","highVolumeMessageEnabled":"...","estimatedWaitingTime":"...","callbackOptionEnabled":"..."},"comfortMessage":{"greeting":"...","enabled":"...","timeBetweenMessages":"...","audioAnnouncementFiles":"..."},"comfortMessageBypass":{"greeting":"...","enabled":"...","callWaitingAgeThreshold":"...","audioAnnouncementFiles":"..."}},"enabled":true,"name":"...","languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","phoneNumber":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



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
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {queue_id}")



@app.command("list-announcements")
def list_announcements(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("announcements", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
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
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
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
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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



@app.command("update-call-forwarding")
def update_call_forwarding(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Forwarding Settings for a Call Queue\n\nExample --json-body:\n  '{"callForwarding":{"always":{"enabled":"...","destination":"...","ringReminderEnabled":"...","destinationVoicemailEnabled":"..."},"selective":{"enabled":"...","destination":"...","ringReminderEnabled":"...","destinationVoicemailEnabled":"..."},"rules":["..."],"modes":["..."]}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-selective-rules")
def create_selective_rules(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the selective rule in the hunt group."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines whe"),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines wh"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Selective Call Forwarding Rule for a Call Queue\n\nExample --json-body:\n  '{"name":"...","callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":"...","unavailableNumberEnabled":"...","numbers":"..."}},"callsTo":{"numbers":["..."]},"enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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



@app.command("update-selective-rules")
def update_selective_rules(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    rule_id: str = typer.Argument(help="ruleId"),
    name: str = typer.Option(None, "--name", help="Unique name for the selective rule in the hunt group."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines whe"),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines wh"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Selective Call Forwarding Rule for a Call Queue\n\nExample --json-body:\n  '{"name":"...","enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":"...","unavailableNumberEnabled":"...","numbers":"..."}},"callsTo":{"numbers":["..."]}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules/{rule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
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
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {rule_id}")



@app.command("list-holiday-service")
def list_holiday_service(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Holiday Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/holidayService"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("audioFiles", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("update-holiday-service")
def update_holiday_service(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    holiday_service_enabled: bool = typer.Option(None, "--holiday-service-enabled/--no-holiday-service-enabled", help="Enable or Disable the call queue holiday service routing pol"),
    action: str = typer.Option(None, "--action", help="Choices: BUSY, TRANSFER"),
    holiday_schedule_level: str = typer.Option(None, "--holiday-schedule-level", help="Choices: LOCATION, ORGANIZATION"),
    holiday_schedule_name: str = typer.Option(None, "--holiday-schedule-name", help="Name of the schedule configured for a holiday service as one"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help="Call gets transferred to this number when action is set to `"),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help="Indicates whether an announcement plays to callers before th"),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Holiday Service\n\nExample --json-body:\n  '{"holidayServiceEnabled":true,"action":"BUSY","holidayScheduleLevel":"LOCATION","playAnnouncementBeforeEnabled":true,"audioMessageSelection":"DEFAULT","holidayScheduleName":"...","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"...","level":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/holidayService"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        if holiday_schedule_name is not None:
            body["holidayScheduleName"] = holiday_schedule_name
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-night-service")
def list_night_service(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Night Service."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/nightService"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("audioFiles", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("update-night-service")
def update_night_service(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    night_service_enabled: bool = typer.Option(None, "--night-service-enabled/--no-night-service-enabled", help="Enable or disable call queue night service routing policy."),
    action: str = typer.Option(None, "--action", help="Choices: BUSY, TRANSFER"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help="Call gets transferred to this number when action is set to `"),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help="Indicates whether an announcement plays to callers before th"),
    announcement_mode: str = typer.Option(None, "--announcement-mode", help="Choices: NORMAL, MANUAL"),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    business_hours_name: str = typer.Option(None, "--business-hours-name", help="Name of the schedule configured for a night service as one o"),
    business_hours_level: str = typer.Option(None, "--business-hours-level", help="Choices: ORGANIZATION, LOCATION"),
    force_night_service_enabled: bool = typer.Option(None, "--force-night-service-enabled/--no-force-night-service-enabled", help="Force night service regardless of business hour schedule."),
    manual_audio_message_selection: str = typer.Option(None, "--manual-audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Night Service\n\nExample --json-body:\n  '{"nightServiceEnabled":true,"playAnnouncementBeforeEnabled":true,"announcementMode":"NORMAL","audioMessageSelection":"DEFAULT","forceNightServiceEnabled":true,"manualAudioMessageSelection":"DEFAULT","action":"BUSY","transferPhoneNumber":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/nightService"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if night_service_enabled is not None:
            body["nightServiceEnabled"] = night_service_enabled
        if action is not None:
            body["action"] = action
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if announcement_mode is not None:
            body["announcementMode"] = announcement_mode
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
        if business_hours_name is not None:
            body["businessHoursName"] = business_hours_name
        if business_hours_level is not None:
            body["businessHoursLevel"] = business_hours_level
        if force_night_service_enabled is not None:
            body["forceNightServiceEnabled"] = force_night_service_enabled
        if manual_audio_message_selection is not None:
            body["manualAudioMessageSelection"] = manual_audio_message_selection
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-forced-forward")
def list_forced_forward(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Forced Forward."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/forcedForward"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("audioFiles", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("update-forced-forward")
def update_forced_forward(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    forced_forward_enabled: bool = typer.Option(None, "--forced-forward-enabled/--no-forced-forward-enabled", help="Enable or disable call forced forward service routing policy"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help="Call gets transferred to this number when action is set to `"),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help="Indicates whether an announcement plays to callers before th"),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Forced Forward service\n\nExample --json-body:\n  '{"forcedForwardEnabled":true,"playAnnouncementBeforeEnabled":true,"audioMessageSelection":"DEFAULT","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"...","level":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/forcedForward"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if forced_forward_enabled is not None:
            body["forcedForwardEnabled"] = forced_forward_enabled
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-stranded-calls")
def list_stranded_calls(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Stranded Calls."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/strandedCalls"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("audioFiles", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("update-stranded-calls")
def update_stranded_calls(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    action: str = typer.Option(None, "--action", help="Choices: NONE, BUSY, TRANSFER, NIGHT_SERVICE, RINGING, ANNOUNCEMENT"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help="Call gets transferred to this number when action is set to `"),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Stranded Calls service\n\nExample --json-body:\n  '{"action":"NONE","audioMessageSelection":"DEFAULT","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"...","level":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/strandedCalls"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if action is not None:
            body["action"] = action
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-available-numbers-queues")
def list_available_numbers_queues(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Primary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/availableNumbers"
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-numbers-alternate")
def list_available_numbers_alternate(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Alternate Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/alternate/availableNumbers"
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-numbers-call-forwarding")
def list_available_numbers_call_forwarding(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `exten"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Call Forward Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/callForwarding/availableNumbers"
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-agents-queues")
def list_available_agents_queues(
    location_id: str = typer.Option(..., "--location-id", help="The location ID of the call queue. Temporary mandatory query"),
    name: str = typer.Option(None, "--name", help="Search based on name (user first and last name combination)."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search based on number or extension."),
    order: str = typer.Option(None, "--order", help="Order the available agents according to the designated field"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Available Agents."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/availableAgents"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("agents", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-supervisors")
def list_supervisors(
    name: str = typer.Option(None, "--name", help="Only return the supervisors that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return the supervisors that match the given phone numbe"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of supervisors with Customer Assist li"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of Supervisors with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    params = {}
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("supervisors", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("create-supervisors")
def create_supervisors(
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Creates a Customer Assist queue supervisor, when `true`. Cus"),
    id_param: str = typer.Option(None, "--id", help="(required) A unique identifier for the supervisor."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Supervisor with Customer Assist\n\nExample --json-body:\n  '{"id":"...","agents":[{"id":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        _missing = [f for f in ['id'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("delete-supervisors-config")
def delete_supervisors_config(
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Include Customer Assist supervisors when true."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Bulk supervisors."""
    if not force:
        typer.confirm("Delete this resource?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo("Deleted.")



@app.command("show-supervisors")
def show_supervisors(
    supervisor_id: str = typer.Argument(help="supervisorId"),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Only return the agents that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return agents that match the given phone number, extens"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true`, to view the details of a supervisor w"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """GET Supervisor Detail with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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



@app.command("update-supervisors")
def update_supervisors(
    supervisor_id: str = typer.Argument(help="supervisorId"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true` to modify a supervisor with Customer A"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign or Unassign Agents to Supervisor with Customer Assist\n\nExample --json-body:\n  '{"agents":[{"id":"...","action":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-supervisors-config-1")
def delete_supervisors_config_1(
    supervisor_id: str = typer.Argument(help="supervisorId"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Include Customer Assist supervisors when true."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete A Supervisor."""
    if not force:
        typer.confirm(f"Delete {supervisor_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {supervisor_id}")



@app.command("list-available-supervisors")
def list_available_supervisors(
    name: str = typer.Option(None, "--name", help="Only return the supervisors that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return the supervisors that match the given phone numbe"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of available supervisors with Customer"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Supervisors with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/availableSupervisors"
    params = {}
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("supervisors", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-agents-supervisors")
def list_available_agents_supervisors(
    name: str = typer.Option(None, "--name", help="Returns only the agents that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the agents that match the phone number, extensi"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of available agents with Customer Assi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Agents with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/availableAgents"
    params = {}
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("agents", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-agents")
def list_agents(
    location_id: str = typer.Option(None, "--location-id", help="Return only the call queue agents in this location."),
    queue_id: str = typer.Option(None, "--queue-id", help="Only return call queue agents with the matching queue ID."),
    name: str = typer.Option(None, "--name", help="Returns only the list of call queue agents that match the gi"),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the list of call queue agents that match the gi"),
    join_enabled: str = typer.Option(None, "--join-enabled", help="Returns only the list of call queue agents that match the gi"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of call queues with Customer Assist li"),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by call queue agent's name, in a"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Queue Agents with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if queue_id is not None:
        params["queueId"] = queue_id
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("agents", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="agents"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("show-agents")
def show_agents(
    id: str = typer.Argument(help="id"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true` to view the details of an agent with C"),
    max: str = typer.Option(..., "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(..., "--start", help="Start at the zero-based offset in the list of matching objec"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Agent with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/{id}"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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



@app.command("update-settings")
def update_settings(
    id: str = typer.Argument(help="id"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true` to modify an agent that has Customer A"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Agent's Settings of One or More Call Queues with Customer Assist\n\nExample --json-body:\n  '{"settings":[{"queueId":"...","joinEnabled":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/{id}/settings"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
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
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    print_json(result)


