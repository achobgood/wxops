import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling hunt-group.")


@app.command("list", short_help="Read the List of Hunt Groups.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Only return hunt groups with matching location ID."),
    name: str = typer.Option(None, "--name", help="Only return hunt groups with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return hunt groups with the matching primary phone number or extension."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Hunt Groups."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/huntGroups"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
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
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("huntGroups", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="huntGroups"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","callPolicies":{"policy":"CIRCULAR","noAnswer":{"nextAgentEnabled":true,"nextAgentRings":0,"forwardEnabled":true,"numberOfRings":0,"destinationVoicemailEnabled":true,"destination":"..."},"waitingEnabled":true,"groupBusyEnabled":true,"allowMembersToControlGroupBusyEnabled":true,"busyRedirect":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"businessContinuityRedirect":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}},"agents":[{"id":"...","weight":"..."}],"enabled":true,"phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","huntGroupCallerIdForOutgoingCallsEnabled":true,"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("create", short_help="Create a Hunt Group.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the hunt group."),
    phone_number: str = typer.Option(None, "--phone-number", help="Primary phone number of the hunt group. Either phone number or extension are required."),
    extension: str = typer.Option(None, "--extension", help="Primary phone extension of the hunt group. Either phone number or extension are required."),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name to be shown when calls are forwarded out of this hunt group. Defaults to `.`. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Last name to be shown when calls are forwarded out of this hunt group. Defaults to the phone number if set, otherwise defaults to call group name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone for the hunt group."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="(required) Whether or not the hunt group is enabled."),
    hunt_group_caller_id_for_outgoing_calls_enabled: bool = typer.Option(None, "--hunt-group-caller-id-for-outgoing-calls-enabled/--no-hunt-group-caller-id-for-outgoing-calls-enabled", help="Enable the hunt group to be used as the caller ID when the agent places outgoing calls. When set to true the hunt group's caller ID will be used."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="The name to be used for dial by name functions. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Hunt Group.\n\n\b\nExample: wxcli hunt-group create LOCATION_ID --json-body '{"name":"...","callPolicies":{"policy":"CIRCULAR","noAnswer":{"nextAgentEnabled":true,"nextAgentRings":0,"forwardEnabled":true,"numberOfRings":0,"destinationVoicemailEnabled":true}},"agents":[{"id":"..."}],"enabled":true}'\n\n\b\nExample --json-body: '{"name":"...","callPolicies":{"policy":"CIRCULAR","noAnswer":{"nextAgentEnabled":true,"nextAgentRings":0,"forwardEnabled":true,"numberOfRings":0,"destinationVoicemailEnabled":true,"destination":"..."},"waitingEnabled":true,"groupBusyEnabled":true,"allowMembersToControlGroupBusyEnabled":true,"busyRedirect":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"businessContinuityRedirect":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}},"agents":[{"id":"...","weight":"..."}],"enabled":true,"phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","huntGroupCallerIdForOutgoingCallsEnabled":true,"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups"
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
        if enabled is not None:
            body["enabled"] = enabled
        if hunt_group_caller_id_for_outgoing_calls_enabled is not None:
            body["huntGroupCallerIdForOutgoingCallsEnabled"] = hunt_group_caller_id_for_outgoing_calls_enabled
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        _missing = [f for f in ['name', 'enabled'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    body.setdefault('callPolicies', {'policy': 'CIRCULAR', 'noAnswer': {'nextAgentEnabled': True, 'nextAgentRings': 3, 'forwardEnabled': False, 'numberOfRings': 15, 'destinationVoicemailEnabled': False}})
    body.setdefault('agents', [])
    body.setdefault('enabled', True)
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



@app.command("show", short_help="Get Details for a Hunt Group.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Hunt Group.\n\n\b\nExample: wxcli hunt-group show LOCATION_ID HUNT_GROUP_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}"
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



_BODY_SKELETON_UPDATE = '{"enabled":true,"name":"...","phoneNumber":"...","extension":"...","distinctiveRing":true,"alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL"}],"languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","callPolicies":{"policy":"CIRCULAR","noAnswer":{"nextAgentEnabled":true,"nextAgentRings":0,"forwardEnabled":true,"numberOfRings":0,"destinationVoicemailEnabled":true,"destination":"..."},"waitingEnabled":true,"groupBusyEnabled":true,"allowMembersToControlGroupBusyEnabled":true,"busyRedirect":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"businessContinuityRedirect":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}},"agents":[{"id":"...","weight":"..."}],"huntGroupCallerIdForOutgoingCallsEnabled":true,"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("update", short_help="Update a Hunt Group.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not the hunt group is enabled."),
    name: str = typer.Option(None, "--name", help="Unique name for the hunt group."),
    phone_number: str = typer.Option(None, "--phone-number", help="Primary phone number of the hunt group."),
    extension: str = typer.Option(None, "--extension", help="Primary phone extension of the hunt group."),
    distinctive_ring: bool = typer.Option(None, "--distinctive-ring/--no-distinctive-ring", help="Whether or not the hunt group has the distinctive ring option enabled."),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name to be shown when calls are forwarded out of this hunt group. Defaults to `.`. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Last name to be shown when calls are forwarded out of this hunt group. Defaults to the phone number if set, otherwise defaults to call group name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone for the hunt group."),
    hunt_group_caller_id_for_outgoing_calls_enabled: bool = typer.Option(None, "--hunt-group-caller-id-for-outgoing-calls-enabled/--no-hunt-group-caller-id-for-outgoing-calls-enabled", help="Enable the hunt group to be used as the caller ID when the agent places outgoing calls. When set to true the hunt group's caller ID will be used."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name functions. To clear the `dialByName`, the attribute must be set to null or empty string. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Hunt Group.\n\n\b\nExample: wxcli hunt-group update LOCATION_ID HUNT_GROUP_ID\n\n\b\nExample --json-body: '{"enabled":true,"name":"...","phoneNumber":"...","extension":"...","distinctiveRing":true,"alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL"}],"languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","callPolicies":{"policy":"CIRCULAR","noAnswer":{"nextAgentEnabled":true,"nextAgentRings":0,"forwardEnabled":true,"numberOfRings":0,"destinationVoicemailEnabled":true,"destination":"..."},"waitingEnabled":true,"groupBusyEnabled":true,"allowMembersToControlGroupBusyEnabled":true,"busyRedirect":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"businessContinuityRedirect":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}},"agents":[{"id":"...","weight":"..."}],"huntGroupCallerIdForOutgoingCallsEnabled":true,"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}"
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
        if name is not None:
            body["name"] = name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if distinctive_ring is not None:
            body["distinctiveRing"] = distinctive_ring
        if language_code is not None:
            body["languageCode"] = language_code
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if time_zone is not None:
            body["timeZone"] = time_zone
        if hunt_group_caller_id_for_outgoing_calls_enabled is not None:
            body["huntGroupCallerIdForOutgoingCallsEnabled"] = hunt_group_caller_id_for_outgoing_calls_enabled
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
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
        emit({"status": "updated", "id": hunt_group_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Hunt Group.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Hunt Group.\n\n\b\nExample: wxcli hunt-group delete LOCATION_ID HUNT_GROUP_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {hunt_group_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}"
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
        typer.echo(f"Deleted: {hunt_group_id}")
    else:
        emit({"status": "deleted", "id": hunt_group_id}, output=output, fields=fields)



@app.command("show-call-forwarding", short_help="Get Call Forwarding Settings for a Hunt Group.")
def show_call_forwarding(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Forwarding Settings for a Hunt Group.\n\n\b\nExample: wxcli hunt-group show-call-forwarding LOCATION_ID HUNT_GROUP_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding"
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



_BODY_SKELETON_UPDATE_CALL_FORWARDING = '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"selective":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"rules":[{"id":"...","enabled":true}],"operatingModes":{"enabled":true,"modes":[{"normalOperationEnabled":true,"id":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","destination":"...","destinationVoicemailEnabled":true}}]}}}'

@app.command("update-call-forwarding", short_help="Update Call Forwarding Settings for a Hunt Group.")
def update_call_forwarding(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Forwarding Settings for a Hunt Group.\n\n\b\nExample: wxcli hunt-group update-call-forwarding LOCATION_ID HUNT_GROUP_ID\n\n\b\nExample --json-body: '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"selective":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"rules":[{"id":"...","enabled":true}],"operatingModes":{"enabled":true,"modes":[{"normalOperationEnabled":true,"id":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","destination":"...","destinationVoicemailEnabled":true}}]}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_FORWARDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding"
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
        emit({"status": "updated", "id": hunt_group_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_SELECTIVE_RULES = '{"name":"...","callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]},"enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."}}'

@app.command("create-selective-rules", short_help="Create a Selective Call Forwarding Rule for a Hunt Group.")
def create_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the selective rule in the hunt group."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines when this selective call forwarding rule is in effect."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines when this selective call forwarding rule is in effect."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Selective Call Forwarding Rule for a Hunt Group.\n\n\b\nExample: wxcli hunt-group create-selective-rules LOCATION_ID HUNT_GROUP_ID --json-body '{"name":"...","callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true}},"callsTo":{"numbers":[{"type":"PRIMARY"}]}}'\n\n\b\nExample --json-body: '{"name":"...","callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]},"enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SELECTIVE_RULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/selectiveRules"
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



@app.command("show-selective-rules", short_help="Get Selective Call Forwarding Rule for a Hunt Group.")
def show_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Forwarding Rule for a Hunt Group.\n\n\b\nExample: wxcli hunt-group show-selective-rules LOCATION_ID HUNT_GROUP_ID RULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/selectiveRules/{rule_id}"
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



_BODY_SKELETON_UPDATE_SELECTIVE_RULES = '{"name":"...","enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]}}'

@app.command("update-selective-rules", short_help="Update a Selective Call Forwarding Rule for a Hunt Group.")
def update_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    name: str = typer.Option(None, "--name", help="Unique name for the selective rule in the hunt group."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines when this selective call forwarding rule is in effect."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines when this selective call forwarding rule is in effect."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Selective Call Forwarding Rule for a Hunt Group.\n\n\b\nExample: wxcli hunt-group update-selective-rules LOCATION_ID HUNT_GROUP_ID RULE_ID\n\n\b\nExample --json-body: '{"name":"...","enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_RULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/selectiveRules/{rule_id}"
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": rule_id}, output=output, fields=fields)



@app.command("delete-selective-rules", short_help="Delete a Selective Call Forwarding Rule for a Hunt Group.")
def delete_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Forwarding Rule for a Hunt Group.\n\n\b\nExample: wxcli hunt-group delete-selective-rules LOCATION_ID HUNT_GROUP_ID RULE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {rule_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/selectiveRules/{rule_id}"
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
        typer.echo(f"Deleted: {rule_id}")
    else:
        emit({"status": "deleted", "id": rule_id}, output=output, fields=fields)



@app.command("list-available-numbers-hunt-groups", short_help="Get Hunt Group Primary Available Phone Numbers.")
def list_available_numbers_hunt_groups(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hunt Group Primary Available Phone Numbers.\n\n\b\nExample: wxcli hunt-group list-available-numbers-hunt-groups LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/availableNumbers"
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
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Telephony Type', 'telephonyType'), ('Toll Free', 'tollFreeNumber')], limit=limit)



@app.command("list-available-numbers-alternate", short_help="Get Hunt Group Alternate Available Phone Numbers.")
def list_available_numbers_alternate(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hunt Group Alternate Available Phone Numbers.\n\n\b\nExample: wxcli hunt-group list-available-numbers-alternate LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/alternate/availableNumbers"
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
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Telephony Type', 'telephonyType'), ('Toll Free', 'tollFreeNumber')], limit=limit)



@app.command("list-available-numbers-call-forwarding", short_help="Get Hunt Group Call Forward Available Phone Numbers.")
def list_available_numbers_call_forwarding(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `extension`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hunt Group Call Forward Available Phone Numbers.\n\n\b\nExample: wxcli hunt-group list-available-numbers-call-forwarding LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/callForwarding/availableNumbers"
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
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('State', 'state'), ('Owner Type', 'owner.type'), ('Owner Name', 'owner.firstName')], limit=limit)



@app.command("switch-mode-for", short_help="Switch Mode for Call Forwarding Settings for a Hunt Group.")
def switch_mode_for(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    hunt_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli hunt-group list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Call Forwarding Settings for a Hunt Group.\n\n\b\nExample: wxcli hunt-group switch-mode-for LOCATION_ID HUNT_GROUP_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/actions/switchMode/invoke"
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


