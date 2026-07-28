import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling location-settings.")


@app.command("list", hidden=True)
@app.command("list-dial-patterns", short_help="Read the List of Dial Patterns.")
def list_dial_patterns(
    dial_plan_id: str = typer.Argument(help="Webex DIAL_PLAN id, from: wxcli call-routing list-dial-plans"),
    dial_pattern: str = typer.Option(None, "--dial-pattern", help="An enterprise dial pattern is represented by a sequence of digits (1-9), followed by optional wildcard characters. Valid wildcard characters are `!` (matches any sequence of digits) and `X` (matches a single digit, 0-9). The `!` wildcard can only occur once at the end and only in an E.164 pattern"),
    order: str = typer.Option(None, "--order", help="Order the dial patterns according to the designated fields. Available sort fields: `dialPattern`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Dial Patterns.\n\n\b\nExample: wxcli location-settings list-dial-patterns DIAL_PLAN_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/dialPlans/{dial_plan_id}/dialPatterns"
    params = {}
    if dial_pattern is not None:
        params["dialPattern"] = dial_pattern
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
    items = result.get("dialPatterns", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-1", hidden=True)
@app.command("list-calling-details", short_help="List Locations Webex Calling Details.")
def list_calling_details(
    name: str = typer.Option(None, "--name", help="List locations whose name contains this string."),
    order: str = typer.Option(None, "--order", help="Sort the list of locations based on `name`, either asc or desc."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Locations Webex Calling Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations"
    params = {}
    if name is not None:
        params["name"] = name
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
            items = result.get("locations", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="locations"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Outside Dial Digit', 'outsideDialDigit'), ('Enforce Outside Dial Digit', 'enforceOutsideDialDigit'), ('Routing Prefix', 'routingPrefix')], limit=limit)



_BODY_SKELETON_CREATE = '{"id":"...","name":"...","timeZone":"...","preferredLanguage":"...","announcementLanguage":"...","address":{"address1":"...","city":"...","state":"...","postalCode":"...","country":"...","address2":"..."}}'

@app.command("create", short_help="Enable a Location for Webex Calling.")
def create(
    id_param: str = typer.Option(None, "--id", help="(required) A unique identifier for the location."),
    name: str = typer.Option(None, "--name", help="(required) The name of the location."),
    time_zone: str = typer.Option(None, "--time-zone", help="(required) Time zone associated with this location. Refer to this link (https://developer.webex.com/docs/api/guides/webex-for-broadworks-developers-guide#webex-meetings-site-timezone) for the format."),
    preferred_language: str = typer.Option(None, "--preferred-language", help="(required) Default email language."),
    announcement_language: str = typer.Option(None, "--announcement-language", help="(required) Location's phone announcement language."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Enable a Location for Webex Calling.\n\n\b\nExample: wxcli location-settings create --id ID_PARAM --name NAME --time-zone TIME_ZONE --preferred-language PREFERRED_LANGUAGE --announcement-language ANNOUNCEMENT_LANGUAGE\n\n\b\nExample --json-body: '{"id":"...","name":"...","timeZone":"...","preferredLanguage":"...","announcementLanguage":"...","address":{"address1":"...","city":"...","state":"...","postalCode":"...","country":"...","address2":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        if name is not None:
            body["name"] = name
        if time_zone is not None:
            body["timeZone"] = time_zone
        if preferred_language is not None:
            body["preferredLanguage"] = preferred_language
        if announcement_language is not None:
            body["announcementLanguage"] = announcement_language
        _missing = [f for f in ['id', 'name', 'timeZone', 'preferredLanguage', 'announcementLanguage'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Location Webex Calling Details.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Webex Calling Details.\n\n\b\nExample: wxcli location-settings show LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}"
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



_BODY_SKELETON_UPDATE = '{"announcementLanguage":"...","callingLineId":{"name":"...","phoneNumber":"..."},"connection":{"type":"ROUTE_GROUP","id":"..."},"externalCallerIdName":"...","pAccessNetworkInfo":"...","outsideDialDigit":"...","enforceOutsideDialDigit":true,"routingPrefix":"..."}'

@app.command("update", short_help="Update Location Webex Calling Details.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    announcement_language: str = typer.Option(None, "--announcement-language", help="Location's phone announcement language."),
    external_caller_id_name: str = typer.Option(None, "--external-caller-id-name", help="External caller ID name value. Unicode characters."),
    p_access_network_info: str = typer.Option(None, "--p-access-network-info", help="Emergency Location Identifier for a location. The `pAccessNetworkInfo` is set only when the location's country is Belgium(`BE`), Germany(`DE`), or France(`FR`)."),
    outside_dial_digit: str = typer.Option(None, "--outside-dial-digit", help="Must dial to reach an outside line. Default is none."),
    enforce_outside_dial_digit: bool = typer.Option(None, "--enforce-outside-dial-digit/--no-enforce-outside-dial-digit", help="True when enforcing outside dial digit at location level to make PSTN calls."),
    routing_prefix: str = typer.Option(None, "--routing-prefix", help="Must dial a prefix when calling between locations having same extension within same location, should be numeric."),
    charge_number: str = typer.Option(None, "--charge-number", help="Set the chargeable number for the line placing the call. When set and [useChargeNumberForPChargeInfo field (GET location)](/docs/api/v1/beta-location-call-settings-with-p-charge-info-support/get-location-webex-calling-details) is true for the location, all PSTN calls placed from this location will..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Location Webex Calling Details.\n\n\b\nExample: wxcli location-settings update LOCATION_ID\n\n\b\nExample --json-body: '{"announcementLanguage":"...","callingLineId":{"name":"...","phoneNumber":"..."},"connection":{"type":"ROUTE_GROUP","id":"..."},"externalCallerIdName":"...","pAccessNetworkInfo":"...","outsideDialDigit":"...","enforceOutsideDialDigit":true,"routingPrefix":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}"
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
        if external_caller_id_name is not None:
            body["externalCallerIdName"] = external_caller_id_name
        if p_access_network_info is not None:
            body["pAccessNetworkInfo"] = p_access_network_info
        if outside_dial_digit is not None:
            body["outsideDialDigit"] = outside_dial_digit
        if enforce_outside_dial_digit is not None:
            body["enforceOutsideDialDigit"] = enforce_outside_dial_digit
        if routing_prefix is not None:
            body["routingPrefix"] = routing_prefix
        if charge_number is not None:
            body["chargeNumber"] = charge_number
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("list-update-routing-prefix", short_help="Get a List of Update Routing Prefix jobs.")
def list_update_routing_prefix(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a List of Update Routing Prefix jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/updateRoutingPrefix"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Tracking ID', 'trackingId'), ('Source User ID', 'sourceUserId'), ('Source Customer ID', 'sourceCustomerId')], limit=limit)



@app.command("show-update-routing-prefix", short_help="Get the job status of Update Routing Prefix job.")
def show_update_routing_prefix(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli location-settings list-update-routing-prefix"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the job status of Update Routing Prefix job.\n\n\b\nExample: wxcli location-settings show-update-routing-prefix JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/updateRoutingPrefix/{job_id}"
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



@app.command("show-errors", short_help="Get job errors for update routing prefix job.")
def show_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli location-settings list-update-routing-prefix"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get job errors for update routing prefix job.\n\n\b\nExample: wxcli location-settings show-errors JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/updateRoutingPrefix/{job_id}/errors"
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



_BODY_SKELETON_CHANGE_ANNOUNCEMENT_LANGUAGE = '{"announcementLanguageCode":"...","agentEnabled":true,"serviceEnabled":true}'

@app.command("change-announcement-language", short_help="Change Announcement Language.")
def change_announcement_language(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    agent_enabled: str = typer.Option(None, "--agent-enabled", help="Set to `true` to change announcement language for existing people and workspaces."),
    service_enabled: str = typer.Option(None, "--service-enabled", help="Set to `true` to change announcement language for existing feature configurations."),
    announcement_language_code: str = typer.Option(None, "--announcement-language-code", help="Language code."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Change Announcement Language.\n\n\b\nExample: wxcli location-settings change-announcement-language LOCATION_ID --announcement-language-code ANNOUNCEMENT_LANGUAGE_CODE\n\n\b\nExample --json-body: '{"announcementLanguageCode":"...","agentEnabled":true,"serviceEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CHANGE_ANNOUNCEMENT_LANGUAGE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/actions/modifyAnnouncementLanguage/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if agent_enabled is not None:
            body["agentEnabled"] = agent_enabled
        if service_enabled is not None:
            body["serviceEnabled"] = service_enabled
        if announcement_language_code is not None:
            body["announcementLanguageCode"] = announcement_language_code
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-emergency-callback-number", short_help="Get a Location Emergency callback number.")
def show_emergency_callback_number(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location Emergency callback number.\n\n\b\nExample: wxcli location-settings show-emergency-callback-number LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/features/emergencyCallbackNumber"
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



_BODY_SKELETON_UPDATE_EMERGENCY_CALLBACK_NUMBER = '{"selected":"LOCATION_NUMBER","locationMemberId":"...","elinExpiryTimeMinutes":0}'

@app.command("update-emergency-callback-number", short_help="Update a Location Emergency callback number.")
def update_emergency_callback_number(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    selected: str = typer.Option(None, "--selected", help="Choices: LOCATION_NUMBER, LOCATION_MEMBER_NUMBER"),
    location_member_id: str = typer.Option(None, "--location-member-id", help="Member ID of user/place/virtual line/hunt group within the location. Required if `LOCATION_MEMBER_NUMBER` is selected."),
    elin_expiry_time_minutes: str = typer.Option(None, "--elin-expiry-time-minutes", help="ELIN (Emergency Location Identification Number) provides location-specific callback information to emergency responders. This field indicates the time in minutes that the ELIN association remains active after being established. Valid values are between 10 and 1440 minutes."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location Emergency callback number.\n\n\b\nExample: wxcli location-settings update-emergency-callback-number LOCATION_ID --selected LOCATION_NUMBER --location-member-id LOCATION_MEMBER_ID\n\n\b\nExample --json-body: '{"selected":"LOCATION_NUMBER","locationMemberId":"...","elinExpiryTimeMinutes":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EMERGENCY_CALLBACK_NUMBER), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/features/emergencyCallbackNumber"
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
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
        if elin_expiry_time_minutes is not None:
            body["elinExpiryTimeMinutes"] = elin_expiry_time_minutes
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



_BODY_SKELETON_VALIDATE_THE_LIST = '{"extensions":["..."]}'

@app.command("validate-the-list", short_help="Validate the List of Extensions.")
def validate_the_list(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate the List of Extensions.\n\n\b\nExample --json-body: '{"extensions":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_THE_LIST), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/actions/validateExtensions/invoke"
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



_BODY_SKELETON_VALIDATE_EXTENSIONS = '{"extensions":["..."]}'

@app.command("validate-extensions", short_help="Validate Extensions.")
def validate_extensions(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate Extensions.\n\n\b\nExample: wxcli location-settings validate-extensions LOCATION_ID\n\n\b\nExample --json-body: '{"extensions":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_EXTENSIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/actions/validateExtensions/invoke"
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



@app.command("show-music-on-hold", short_help="Get Music On Hold.")
def show_music_on_hold(
    location_id: str = typer.Argument(help="from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Music On Hold.\n\n\b\nExample: wxcli location-settings show-music-on-hold LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/musicOnHold"
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

@app.command("update-music-on-hold", short_help="Update Music On Hold.")
def update_music_on_hold(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    moh_enabled: bool = typer.Option(None, "--moh-enabled/--no-moh-enabled", help="Music on hold is enabled or disabled for the workspace."),
    greeting: str = typer.Option(None, "--greeting", help="Choices: DEFAULT, CUSTOM"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Music On Hold.\n\n\b\nExample: wxcli location-settings update-music-on-hold LOCATION_ID\n\n\b\nExample --json-body: '{"mohEnabled":true,"greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MUSIC_ON_HOLD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/musicOnHold"
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("show-private-network-connect", short_help="Get Private Network Connect.")
def show_private_network_connect(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Private Network Connect.\n\n\b\nExample: wxcli location-settings show-private-network-connect LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/privateNetworkConnect"
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



_BODY_SKELETON_UPDATE_PRIVATE_NETWORK_CONNECT = '{"networkConnectionType":"PUBLIC_INTERNET"}'

@app.command("update-private-network-connect", short_help="Update Private Network Connect.")
def update_private_network_connect(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    network_connection_type: str = typer.Option(None, "--network-connection-type", help="Choices: PUBLIC_INTERNET, PRIVATE_NETWORK"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Private Network Connect.\n\n\b\nExample: wxcli location-settings update-private-network-connect LOCATION_ID --network-connection-type PUBLIC_INTERNET\n\n\b\nExample --json-body: '{"networkConnectionType":"PUBLIC_INTERNET"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PRIVATE_NETWORK_CONNECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/privateNetworkConnect"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if network_connection_type is not None:
            body["networkConnectionType"] = network_connection_type
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("list-route-choices", short_help="Read the List of Routing Choices.")
def list_route_choices(
    route_group_name: str = typer.Option(None, "--route-group-name", help="Return the list of route identities matching the Route group name."),
    trunk_name: str = typer.Option(None, "--trunk-name", help="Return the list of route identities matching the Trunk name."),
    order: str = typer.Option(None, "--order", help="Order the route identities according to the designated fields. Available sort fields: `routeName`, `routeType`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Routing Choices."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/routeChoices"
    params = {}
    if route_group_name is not None:
        params["routeGroupName"] = route_group_name
    if trunk_name is not None:
        params["trunkName"] = trunk_name
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
    items = result.get("routeIdentities", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type')], limit=limit)



@app.command("list-available-numbers-external-caller-id", short_help="Get the List of Phone Numbers Available for External Caller ID.")
def list_available_numbers_external_caller_id(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the provided list in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    person_id: str = typer.Option(None, "--person-id", help="Retrieve available external caller ID numbers for this person. If `personId` is not provided it may result in the unsuccessful assignment of the returned number. This parameter has no effect when workspace or virtual line ID is used."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the List of Phone Numbers Available for External Caller ID.\n\n\b\nExample: wxcli location-settings list-available-numbers-external-caller-id LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/externalCallerId/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if owner_name is not None:
        params["ownerName"] = owner_name
    if person_id is not None:
        params["personId"] = person_id
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('Routing Prefix', 'routingPrefix'), ('ESN', 'esn'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-locations", short_help="Get Available Phone Numbers for a Location with Given Criteria.")
def list_available_numbers_locations(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Phone Numbers for a Location with Given Criteria.\n\n\b\nExample: wxcli location-settings list-available-numbers-locations LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/availableNumbers"
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



@app.command("list-available-numbers-webex-go", short_help="Get Webex Go Available Phone Numbers.")
def list_available_numbers_webex_go(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Webex Go Available Phone Numbers.\n\n\b\nExample: wxcli location-settings list-available-numbers-webex-go LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/webexGo/availableNumbers"
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



@app.command("list-available-numbers-emergency-callback-number", short_help="Get Location ECBN Available Phone Numbers.")
def list_available_numbers_emergency_callback_number(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location ECBN Available Phone Numbers.\n\n\b\nExample: wxcli location-settings list-available-numbers-emergency-callback-number LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/emergencyCallbackNumber/availableNumbers"
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



@app.command("list-available-numbers-call-intercept", short_help="Get Location Call Intercept Available Phone Numbers.")
def list_available_numbers_call_intercept(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    extension: str = typer.Option(None, "--extension", help="Returns the list of phone numbers with the given `extension`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Call Intercept Available Phone Numbers.\n\n\b\nExample: wxcli location-settings list-available-numbers-call-intercept LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callIntercept/availableNumbers"
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



@app.command("list-directories", short_help="Read list of Receptionist Contact Directories.")
def list_directories(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read list of Receptionist Contact Directories.\n\n\b\nExample: wxcli location-settings list-directories LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/receptionistContacts/directories"
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
    items = result.get("directories", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



_BODY_SKELETON_CREATE_DIRECTORIES = '{"name":"...","contacts":[{"personId":"...","featureId":"...","type":"..."}]}'

@app.command("create-directories", short_help="Create a Receptionist Contact Directory.")
def create_directories(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="(required) Receptionist Contact Directory name. The directory name should be greater than 0 and less than 41 characters in length."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Receptionist Contact Directory.\n\n\b\nExample: wxcli location-settings create-directories LOCATION_ID --name NAME\n\n\b\nExample --json-body: '{"name":"...","contacts":[{"personId":"...","featureId":"...","type":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DIRECTORIES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/receptionistContacts/directories"
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



@app.command("show-directories", short_help="Get details for a Receptionist Contact Directory.")
def show_directories(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    directory_id: str = typer.Argument(help="Webex DEPARTMENT id, from: wxcli location-settings list-directories"),
    search_criteria_mode_or: str = typer.Option(None, "--search-criteria-mode-or", help="When `true`, results matching any one of the search criteria are included. The value can only be `true` or not included in the request. Specifying `searchCriteriaModeOr` without any search criteria, or setting it to `false` results in an `ErrorResponse`. If no search criteria is specified, all..."),
    first_name: str = typer.Option(None, "--first-name", help="Search for directories that contain people with the indicated first name."),
    last_name: str = typer.Option(None, "--last-name", help="Search for directories that contain people with the indicated last name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for directories that contain people with the indicated phone number."),
    extension: str = typer.Option(None, "--extension", help="Search for directories that contain people with the indicated extension."),
    person_id: str = typer.Option(None, "--person-id", help="Search for directories that contain people with the indicated person ID."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get details for a Receptionist Contact Directory.\n\n\b\nExample: wxcli location-settings show-directories LOCATION_ID DIRECTORY_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/receptionistContacts/directories/{directory_id}"
    params = {}
    if search_criteria_mode_or is not None:
        params["searchCriteriaModeOr"] = search_criteria_mode_or
    if first_name is not None:
        params["firstName"] = first_name
    if last_name is not None:
        params["lastName"] = last_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    if person_id is not None:
        params["personId"] = person_id
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



_BODY_SKELETON_UPDATE_DIRECTORIES = '{"name":"...","contacts":["..."]}'

@app.command("update-directories", short_help="Modify a Receptionist Contact Directory.")
def update_directories(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    directory_id: str = typer.Argument(help="Webex DEPARTMENT id, from: wxcli location-settings list-directories"),
    name: str = typer.Option(None, "--name", help="Receptionist Contact Directory name. The directory name should be greater than 0 and less than 41 characters in length."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Receptionist Contact Directory.\n\n\b\nExample: wxcli location-settings update-directories LOCATION_ID DIRECTORY_ID --name NAME\n\n\b\nExample --json-body: '{"name":"...","contacts":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DIRECTORIES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/receptionistContacts/directories/{directory_id}"
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
        emit({"status": "updated", "id": directory_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Receptionist Contact Directory.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    directory_id: str = typer.Argument(help="Webex SCIM_GROUP id, from: wxcli location-settings list-directories"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Receptionist Contact Directory.\n\n\b\nExample: wxcli location-settings delete LOCATION_ID DIRECTORY_ID"""
    if not force:
        typer.confirm(f"Delete {directory_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/receptionistContacts/directories/{directory_id}"
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
        typer.echo(f"Deleted: {directory_id}")
    else:
        emit({"status": "deleted", "id": directory_id}, output=output, fields=fields)



@app.command("list-available-numbers-charge-number", short_help="Get Available Charge Numbers for a Location with Given Criteria.")
def list_available_numbers_charge_number(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Charge Numbers for a Location with Given Criteria.\n\n\b\nExample: wxcli location-settings list-available-numbers-charge-number LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/chargeNumber/availableNumbers"
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber'), ('Is Service Number', 'isServiceNumber')], limit=limit)



@app.command("list-delete-calling-location", short_help="Get a List of Disable Calling Location Jobs.")
def list_delete_calling_location(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a List of Disable Calling Location Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Location Name', 'locationName'), ('Tracking ID', 'trackingId'), ('Source User ID', 'sourceUserId')], limit=limit)



_BODY_SKELETON_CREATE_DELETE_CALLING_LOCATION = '{"locationId":"...","locationName":"...","forceDelete":true}'

@app.command("create-delete-calling-location", short_help="Disable a Location for Webex Calling.")
def create_delete_calling_location(
    location_id: str = typer.Option(None, "--location-id", help="(required) Unique identifier for the calling location to disable."),
    location_name: str = typer.Option(None, "--location-name", help="Name of the calling location to disable."),
    force_delete: bool = typer.Option(None, "--force-delete/--no-force-delete", help="Force delete is only applicable when calling features like call queues, hunt groups, virtual lines, etc or a trunk that is not in use exists in the calling location and customer still wants to disable the calling location."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Disable a Location for Webex Calling.\n\n\b\nExample: wxcli location-settings create-delete-calling-location --location-id LOCATION_ID\n\n\b\nExample --json-body: '{"locationId":"...","locationName":"...","forceDelete":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DELETE_CALLING_LOCATION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if location_id is not None:
            body["locationId"] = location_id
        if location_name is not None:
            body["locationName"] = location_name
        if force_delete is not None:
            body["forceDelete"] = force_delete
        _missing = [f for f in ['locationId'] if f not in body or body[f] is None]
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



@app.command("safe-delete-check", short_help="Safe Delete Check Before Disabling a Location for Webex Calling.")
def safe_delete_check(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Safe Delete Check Before Disabling a Location for Webex Calling.\n\n\b\nExample: wxcli location-settings safe-delete-check LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/actions/precheckForDeletion/invoke"
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



@app.command("pause-a-disable", short_help="Pause a Disable Calling Location Job.")
def pause_a_disable(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli location-settings list-delete-calling-location"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause a Disable Calling Location Job.\n\n\b\nExample: wxcli location-settings pause-a-disable JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation/{job_id}/actions/pause/invoke"
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



@app.command("resume-a-paused", short_help="Resume a Paused Disable Calling Location Job.")
def resume_a_paused(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli location-settings list-delete-calling-location"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume a Paused Disable Calling Location Job.\n\n\b\nExample: wxcli location-settings resume-a-paused JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation/{job_id}/actions/resume/invoke"
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



@app.command("list-errors", short_help="Retrieve Errors for a Disable Calling Location Job.")
def list_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli location-settings list-delete-calling-location"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Errors for a Disable Calling Location Job.\n\n\b\nExample: wxcli location-settings list-errors JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation/{job_id}/errors"
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
    emit(items, output=output, fields=fields, columns=[('Tracking ID', 'trackingId'), ('Item Number', 'itemNumber'), ('Item', 'item')], limit=limit)



@app.command("show-delete-calling-location", short_help="Get Disable Calling Location Job Status.")
def show_delete_calling_location(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli location-settings list-delete-calling-location"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Disable Calling Location Job Status.\n\n\b\nExample: wxcli location-settings show-delete-calling-location JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation/{job_id}"
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



@app.command("show-call-captions", short_help="Get the location call captions settings.")
def show_call_captions(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the location call captions settings.\n\n\b\nExample: wxcli location-settings show-call-captions LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callCaptions"
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



_BODY_SKELETON_UPDATE_CALL_CAPTIONS = '{"locationClosedCaptionsEnabled":true,"locationTranscriptsEnabled":true,"useOrgSettingsEnabled":true}'

@app.command("update-call-captions", short_help="Update the location call captions settings.")
def update_call_captions(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    location_closed_captions_enabled: bool = typer.Option(None, "--location-closed-captions-enabled/--no-location-closed-captions-enabled", help="Enable or disable location-level closed captions."),
    location_transcripts_enabled: bool = typer.Option(None, "--location-transcripts-enabled/--no-location-transcripts-enabled", help="Enable or disable location-level transcripts."),
    use_org_settings_enabled: bool = typer.Option(None, "--use-org-settings-enabled/--no-use-org-settings-enabled", help="If `useOrgSettingsEnabled` is `true`, organization-level settings will control the location's closed captions and transcripts. Otherwise, location-level settings are used."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the location call captions settings.\n\n\b\nExample: wxcli location-settings update-call-captions LOCATION_ID\n\n\b\nExample --json-body: '{"locationClosedCaptionsEnabled":true,"locationTranscriptsEnabled":true,"useOrgSettingsEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_CAPTIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callCaptions"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if location_closed_captions_enabled is not None:
            body["locationClosedCaptionsEnabled"] = location_closed_captions_enabled
        if location_transcripts_enabled is not None:
            body["locationTranscriptsEnabled"] = location_transcripts_enabled
        if use_org_settings_enabled is not None:
            body["useOrgSettingsEnabled"] = use_org_settings_enabled
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)


