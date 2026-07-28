import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling location-call-handling.")


_BODY_SKELETON_GENERATE_EXAMPLE_PASSWORD = '{"generate":["sip"]}'

@app.command("generate-example-password", short_help="Generate example password for Location.")
def generate_example_password(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate example password for Location.\n\n\b\nExample: wxcli location-call-handling generate-example-password LOCATION_ID\n\n\b\nExample --json-body: '{"generate":["sip"]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_GENERATE_EXAMPLE_PASSWORD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/actions/generatePassword/invoke"
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



@app.command("show", short_help="Read the Internal Dialing configuration for a location.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the Internal Dialing configuration for a location.\n\n\b\nExample: wxcli location-call-handling show LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/internalDialing"
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



_BODY_SKELETON_UPDATE = '{"enableUnknownExtensionRoutePolicy":true,"unknownExtensionRouteIdentity":{"id":"...","type":"ROUTE_GROUP"}}'

@app.command("update", short_help="Modify the Internal Dialing configuration for a location.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    enable_unknown_extension_route_policy: bool = typer.Option(None, "--enable-unknown-extension-route-policy/--no-enable-unknown-extension-route-policy", help="When enabled, calls made by users at the location to an unknown extension (between 2-6 digits) are routed to the selected route group/trunk as premises calls."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify the Internal Dialing configuration for a location.\n\n\b\nExample: wxcli location-call-handling update LOCATION_ID\n\n\b\nExample --json-body: '{"enableUnknownExtensionRoutePolicy":true,"unknownExtensionRouteIdentity":{"id":"...","type":"ROUTE_GROUP"}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/internalDialing"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enable_unknown_extension_route_policy is not None:
            body["enableUnknownExtensionRoutePolicy"] = enable_unknown_extension_route_policy
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



@app.command("show-intercept", short_help="Get Location Intercept.")
def show_intercept(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Intercept.\n\n\b\nExample: wxcli location-call-handling show-intercept LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/intercept"
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



_BODY_SKELETON_UPDATE_INTERCEPT = '{"enabled":true,"incoming":{"type":"INTERCEPT_ALL","voicemailEnabled":true,"announcements":{"greeting":"...","fileName":"...","newNumber":"...","zeroTransfer":"..."}},"outgoing":{"type":"INTERCEPT_ALL","transferEnabled":true,"destination":"..."}}'

@app.command("update-intercept", short_help="Put Location Intercept.")
def update_intercept(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable/disable location intercept. Enable this feature to override any location's Call Intercept settings that a person configures."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Put Location Intercept.\n\n\b\nExample: wxcli location-call-handling update-intercept LOCATION_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true,"incoming":{"type":"INTERCEPT_ALL","voicemailEnabled":true,"announcements":{"greeting":"...","fileName":"...","newNumber":"...","zeroTransfer":"..."}},"outgoing":{"type":"INTERCEPT_ALL","transferEnabled":true,"destination":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_INTERCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/intercept"
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("list", short_help="Get Location Outgoing Permission.")
def cmd_list(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Outgoing Permission.\n\n\b\nExample: wxcli location-call-handling list LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission"
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



_BODY_SKELETON_UPDATE_OUTGOING_PERMISSION = '{"callingPermissions":[{"callType":"...","action":"...","transferEnabled":"..."}]}'

@app.command("update-outgoing-permission", short_help="Update Location Outgoing Permission.")
def update_outgoing_permission(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Location Outgoing Permission.\n\n\b\nExample: wxcli location-call-handling update-outgoing-permission LOCATION_ID\n\n\b\nExample --json-body: '{"callingPermissions":[{"callType":"...","action":"...","transferEnabled":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_OUTGOING_PERMISSION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission"
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("show-auto-transfer-numbers", short_help="Get Outgoing Permission Auto Transfer Number.")
def show_auto_transfer_numbers(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Outgoing Permission Auto Transfer Number.\n\n\b\nExample: wxcli location-call-handling show-auto-transfer-numbers LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/autoTransferNumbers"
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



_BODY_SKELETON_UPDATE_AUTO_TRANSFER_NUMBERS = '{"autoTransferNumber1":"...","autoTransferNumber2":"...","autoTransferNumber3":"..."}'

@app.command("update-auto-transfer-numbers", short_help="Put Outgoing Permission Auto Transfer Number.")
def update_auto_transfer_numbers(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_transfer_number1: str = typer.Option(None, "--auto-transfer-number1", help="Calls placed meeting the criteria in an outbound rule whose `action` is `TRANSFER_NUMBER_1` will be transferred to this number."),
    auto_transfer_number2: str = typer.Option(None, "--auto-transfer-number2", help="Calls placed meeting the criteria in an outbound rule whose `action` is `TRANSFER_NUMBER_2` will be transferred to this number."),
    auto_transfer_number3: str = typer.Option(None, "--auto-transfer-number3", help="Calls placed meeting the criteria in an outbound rule whose `action` is `TRANSFER_NUMBER_3` will be transferred to this number."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Put Outgoing Permission Auto Transfer Number.\n\n\b\nExample: wxcli location-call-handling update-auto-transfer-numbers LOCATION_ID\n\n\b\nExample --json-body: '{"autoTransferNumber1":"...","autoTransferNumber2":"...","autoTransferNumber3":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_AUTO_TRANSFER_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/autoTransferNumbers"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("show-access-codes", short_help="Get Outgoing Permission Location Access Code.")
def show_access_codes(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Outgoing Permission Location Access Code.\n\n\b\nExample: wxcli location-call-handling show-access-codes LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/accessCodes"
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



_BODY_SKELETON_CREATE = '{"accessCodes":{"code":"...","description":"..."}}'

@app.command("create", short_help="Create Outgoing Permission a new access code for a customer location.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Outgoing Permission a new access code for a customer location.\n\n\b\nExample: wxcli location-call-handling create LOCATION_ID\n\n\b\nExample --json-body: '{"accessCodes":{"code":"...","description":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/accessCodes"
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
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ACCESS_CODES = '{"deleteCodes":["..."]}'

@app.command("update-access-codes", short_help="Delete Outgoing Permission Access Code Location.")
def update_access_codes(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Outgoing Permission Access Code Location.\n\n\b\nExample: wxcli location-call-handling update-access-codes LOCATION_ID\n\n\b\nExample --json-body: '{"deleteCodes":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ACCESS_CODES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/accessCodes"
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
        emit({"status": "deleted", "id": location_id}, output=output, fields=fields)



@app.command("delete", hidden=True)
@app.command("delete-access-codes-all", short_help="Delete all Outgoing Permission Access Code for a Location.")
def delete_access_codes_all(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete all Outgoing Permission Access Code for a Location.\n\n\b\nExample: wxcli location-call-handling delete-access-codes-all LOCATION_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Access Codes for {location_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/accessCodes"
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
        typer.echo(f"Deleted: {location_id}")
    else:
        emit({"status": "deleted", "id": location_id}, output=output, fields=fields)



@app.command("list-digit-patterns", short_help="Get Outgoing Permission Digit Pattern for a Location.")
def list_digit_patterns(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Outgoing Permission Digit Pattern for a Location.\n\n\b\nExample: wxcli location-call-handling list-digit-patterns LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/digitPatterns"
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

@app.command("create-digit-patterns", short_help="Create Outgoing Permission a new Digit Pattern for a location.")
def create_digit_patterns(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
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
    """Create Outgoing Permission a new Digit Pattern for a location.\n\n\b\nExample: wxcli location-call-handling create-digit-patterns LOCATION_ID --name NAME --pattern PATTERN --action ALLOW --transfer-enabled\n\n\b\nExample --json-body: '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DIGIT_PATTERNS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/digitPatterns"
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



@app.command("delete-digit-patterns-outgoing-permission", short_help="Delete all Outgoing Permission Digit Patterns for a Location.")
def delete_digit_patterns_outgoing_permission(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete all Outgoing Permission Digit Patterns for a Location.\n\n\b\nExample: wxcli location-call-handling delete-digit-patterns-outgoing-permission LOCATION_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Digit Patterns for {location_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/digitPatterns"
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
        typer.echo(f"Deleted: {location_id}")
    else:
        emit({"status": "deleted", "id": location_id}, output=output, fields=fields)



@app.command("show-digit-patterns", short_help="Get Details for a Outgoing Permission Digit Pattern for a Location.")
def show_digit_patterns(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-call-handling list-digit-patterns"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Outgoing Permission Digit Pattern for a Location.\n\n\b\nExample: wxcli location-call-handling show-digit-patterns LOCATION_ID DIGIT_PATTERN_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
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



_BODY_SKELETON_UPDATE_DIGIT_PATTERNS = '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'

@app.command("update-digit-patterns", short_help="Update a Outgoing Permission Digit Pattern for a Location.")
def update_digit_patterns(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-call-handling list-digit-patterns"),
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
    """Update a Outgoing Permission Digit Pattern for a Location.\n\n\b\nExample: wxcli location-call-handling update-digit-patterns LOCATION_ID DIGIT_PATTERN_ID\n\n\b\nExample --json-body: '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DIGIT_PATTERNS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
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



@app.command("delete-digit-patterns-outgoing-permission-1", short_help="Delete a Outgoing Permission Digit Pattern for a Location.")
def delete_digit_patterns_outgoing_permission_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli location-call-handling list-digit-patterns"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Outgoing Permission Digit Pattern for a Location.\n\n\b\nExample: wxcli location-call-handling delete-digit-patterns-outgoing-permission-1 LOCATION_ID DIGIT_PATTERN_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {digit_pattern_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
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


