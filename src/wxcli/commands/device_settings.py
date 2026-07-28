import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling device-settings.")


@app.command("list", short_help="Get Device Members.")
def cmd_list(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Members.\n\n\b\nExample: wxcli device-settings list DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/members"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Extension', 'extension'), ('Line Type', 'lineType')], limit=limit)



_BODY_SKELETON_UPDATE = '{"members":[{"port":"...","id":"...","primaryOwner":"...","lineType":"...","lineWeight":"...","hotlineEnabled":"...","hotlineDestination":"...","allowCallDeclineEnabled":"..."}]}'

@app.command("update", short_help="Update Members on the device.")
def update(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Members on the device.\n\n\b\nExample: wxcli device-settings update DEVICE_ID\n\n\b\nExample --json-body: '{"members":[{"port":"...","id":"...","primaryOwner":"...","lineType":"...","lineWeight":"...","hotlineEnabled":"...","hotlineDestination":"...","allowCallDeclineEnabled":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/members"
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
        emit({"status": "updated", "id": device_id}, output=output, fields=fields)



@app.command("list-available-members", short_help="Search Members.")
def list_available_members(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    member_name: str = typer.Option(None, "--member-name", help="Search (Contains) numbers based on member name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number."),
    location_id: str = typer.Option(None, "--location-id", help="Unique identifier for the location."),
    extension: str = typer.Option(None, "--extension", help="Search (Contains) based on extension."),
    usage_type: str = typer.Option(None, "--usage-type", help="Choices: DEVICE_OWNER, SHARED_LINE"),
    order: str = typer.Option(None, "--order", help="Sort the list of available members on the device in ascending order by name, use either last name `lname` or first name `fname`. Default: last name in ascending order."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Members.\n\n\b\nExample: wxcli device-settings list-available-members DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/availableMembers"
    params = {}
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if location_id is not None:
        params["locationId"] = location_id
    if extension is not None:
        params["extension"] = extension
    if usage_type is not None:
        params["usageType"] = usage_type
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Member Type', 'memberType')], limit=limit)



@app.command("show", short_help="Get Count of Members.")
def show(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    member_name: str = typer.Option(None, "--member-name", help="Search (Contains) numbers based on member name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number."),
    location_id: str = typer.Option(None, "--location-id", help="Unique identifier for the location."),
    extension: str = typer.Option(None, "--extension", help="Search (Contains) based on extension."),
    usage_type: str = typer.Option(None, "--usage-type", help="Choices: DEVICE_OWNER, SHARED_LINE"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Count of Members.\n\n\b\nExample: wxcli device-settings show DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/availableMembers/count"
    params = {}
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if location_id is not None:
        params["locationId"] = location_id
    if extension is not None:
        params["extension"] = extension
    if usage_type is not None:
        params["usageType"] = usage_type
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



@app.command("show-count-available-members", short_help="Get Count of Available Members.")
def show_count_available_members(
    member_name: str = typer.Option(None, "--member-name", help="Search (Contains) numbers based on member name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number."),
    location_id: str = typer.Option(None, "--location-id", help="Unique identifier for the location."),
    extension: str = typer.Option(None, "--extension", help="Search (Contains) based on extension."),
    usage_type: str = typer.Option(None, "--usage-type", help="Choices: DEVICE_OWNER, SHARED_LINE"),
    exclude_virtual_line: str = typer.Option(None, "--exclude-virtual-line", help="If true, filters out virtual lines from the available members list."),
    device_location_id: str = typer.Option(None, "--device-location-id", help="Unique identifier for the device's location. When specified, filters available members to those in the same location as the device."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Count of Available Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/availableMembers/count"
    params = {}
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if location_id is not None:
        params["locationId"] = location_id
    if extension is not None:
        params["extension"] = extension
    if usage_type is not None:
        params["usageType"] = usage_type
    if exclude_virtual_line is not None:
        params["excludeVirtualLine"] = exclude_virtual_line
    if device_location_id is not None:
        params["deviceLocationId"] = device_location_id
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



@app.command("apply-changes-for", short_help="Apply Changes for a specific device.")
def apply_changes_for(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Apply Changes for a specific device.\n\n\b\nExample: wxcli device-settings apply-changes-for DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/actions/applyChanges/invoke"
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



@app.command("show-settings-devices", short_help="Get Device Settings.")
def show_settings_devices(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    device_model: str = typer.Option(None, "--device-model", help="The model type of the device. The corresponding device model display name sometimes called the product name, can also be used to specify the model."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Settings.\n\n\b\nExample: wxcli device-settings show-settings-devices DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/settings"
    params = {}
    if device_model is not None:
        params["deviceModel"] = device_model
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



_BODY_SKELETON_UPDATE_SETTINGS_DEVICES = '{"customizations":{"ata":{"audioCodecPriority":"...","ataDtmfMode":"...","ataDtmfMethod":"...","cdpEnabled":"...","lldpEnabled":"...","qosEnabled":"...","vlan":"...","webAccessEnabled":"..."},"mpp":{"pnacEnabled":"...","audioCodecPriority":"...","backlightTimer":"...","background":"...","cdpEnabled":"...","defaultLoggingLevel":"...","dndServicesEnabled":"...","acd":"..."},"wifi":{"audioCodecPriority":"...","ldap":"...","webAccess":"...","phoneSecurityPwd":"..."}},"customEnabled":true}'

@app.command("update-settings-devices", short_help="Update device settings.")
def update_settings_devices(
    device_id: str = typer.Argument(help="Webex DEVICE id, from: wxcli devices list"),
    device_model: str = typer.Option(None, "--device-model", help="The model type of the device. The corresponding device model display name sometimes called the product name, can also be used to specify the model."),
    custom_enabled: bool = typer.Option(None, "--custom-enabled/--no-custom-enabled", help="Indicates if customization is allowed at a device level. If true, customized at a device level. If false, not customized; uses customer-level configuration."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update device settings.\n\n\b\nExample: wxcli device-settings update-settings-devices DEVICE_ID --custom-enabled\n\n\b\nExample --json-body: '{"customizations":{"ata":{"audioCodecPriority":"...","ataDtmfMode":"...","ataDtmfMethod":"...","cdpEnabled":"...","lldpEnabled":"...","qosEnabled":"...","vlan":"...","webAccessEnabled":"..."},"mpp":{"pnacEnabled":"...","audioCodecPriority":"...","backlightTimer":"...","background":"...","cdpEnabled":"...","defaultLoggingLevel":"...","dndServicesEnabled":"...","acd":"..."},"wifi":{"audioCodecPriority":"...","ldap":"...","webAccess":"...","phoneSecurityPwd":"..."}},"customEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS_DEVICES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/settings"
    params = {}
    if device_model is not None:
        params["deviceModel"] = device_model
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if custom_enabled is not None:
            body["customEnabled"] = custom_enabled
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
        emit({"status": "updated", "id": device_id}, output=output, fields=fields)



@app.command("show-settings-devices-1", short_help="Get Location Device Settings.")
def show_settings_devices_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Device Settings.\n\n\b\nExample: wxcli device-settings show-settings-devices-1 LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/devices/settings"
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



@app.command("show-devices", short_help="Get Webex Calling Device Details.")
def show_devices(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Webex Calling Device Details.\n\n\b\nExample: wxcli device-settings show-devices DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}"
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



_BODY_SKELETON_UPDATE_DEVICES_CONFIG = '{"sipPassword":"..."}'

@app.command("update-devices-config", short_help="Update Third Party Device.")
def update_devices_config(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    sip_password: str = typer.Option(None, "--sip-password", help="Password to be updated."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Third Party Device.\n\n\b\nExample: wxcli device-settings update-devices-config DEVICE_ID --sip-password SIP_PASSWORD\n\n\b\nExample --json-body: '{"sipPassword":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DEVICES_CONFIG), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if sip_password is not None:
            body["sipPassword"] = sip_password
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
        emit({"status": "updated", "id": device_id}, output=output, fields=fields)



@app.command("list-devices-people", short_help="Get Person Devices.")
def list_devices_people(
    person_id: str = typer.Argument(help="Webex PERSON id, from: wxcli people list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Devices.\n\n\b\nExample: wxcli device-settings list-devices-people PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/devices"
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
    items = result.get("devices", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Model', 'model'), ('MAC', 'mac'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_UPDATE_HOTELING = '{"hoteling":{"enabled":true,"limitGuestUse":true,"guestHoursLimit":0}}'

@app.command("update-hoteling", short_help="Modify Hoteling Settings for a Person's Primary Devices.")
def update_hoteling(
    person_id: str = typer.Argument(help="Webex PERSON id, from: wxcli people list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Hoteling Settings for a Person's Primary Devices.\n\n\b\nExample: wxcli device-settings update-hoteling PERSON_ID\n\n\b\nExample --json-body: '{"hoteling":{"enabled":true,"limitGuestUse":true,"guestHoursLimit":0}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_HOTELING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/devices/settings/hoteling"
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



@app.command("list-devices-workspaces", short_help="Get Workspace Devices.")
def list_devices_workspaces(
    workspace_id: str = typer.Argument(help="Webex PERSON id, from: wxcli workspaces list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace Devices.\n\n\b\nExample: wxcli device-settings list-devices-workspaces WORKSPACE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/devices"
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
    items = result.get("devices", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Model', 'model'), ('MAC', 'mac'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_UPDATE_DEVICES_WORKSPACES = '{"enabled":true,"limitGuestUse":true,"guestHoursLimit":0}'

@app.command("update-devices-workspaces", short_help="Modify Workspace Devices.")
def update_devices_workspaces(
    workspace_id: str = typer.Argument(help="Webex PERSON id, from: wxcli workspaces list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable/Disable hoteling Host. Enabling the device for hoteling means that a guest(end user) can log into this host(workspace device) and use this device as if it were their own. This is useful when traveling to a remote office but still needing to place/receive calls with their telephone number and..."),
    limit_guest_use: bool = typer.Option(None, "--limit-guest-use/--no-limit-guest-use", help="Enable limiting the time a guest can use the device. The time limit is configured via `guestHoursLimit`."),
    guest_hours_limit: str = typer.Option(None, "--guest-hours-limit", help="Time Limit in hours until hoteling is enabled. Mandatory if `limitGuestUse` is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Workspace Devices.\n\n\b\nExample: wxcli device-settings update-devices-workspaces WORKSPACE_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true,"limitGuestUse":true,"guestHoursLimit":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DEVICES_WORKSPACES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/devices"
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
        if limit_guest_use is not None:
            body["limitGuestUse"] = limit_guest_use
        if guest_hours_limit is not None:
            body["guestHoursLimit"] = guest_hours_limit
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
        emit({"status": "updated", "id": workspace_id}, output=output, fields=fields)



@app.command("show-settings-devices-2", short_help="Read the device override settings for a organization.")
def show_settings_devices_2(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the device override settings for a organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/settings"
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



@app.command("list-line-key-templates", short_help="Read the list of Line Key Templates.")
def list_line_key_templates(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the list of Line Key Templates."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/lineKeyTemplates"
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
    items = result.get("lineKeyTemplates", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Template Name', 'templateName'), ('Device Model', 'deviceModel'), ('Display Name', 'modelDisplayName')], limit=limit)



_BODY_SKELETON_CREATE = '{"templateName":"...","deviceModel":"...","lineKeys":[{"lineKeyIndex":"...","lineKeyType":"...","sharedLineIndex":"...","lineKeyLabel":"...","lineKeyValue":"..."}],"userReorderEnabled":true}'

@app.command("create", short_help="Create a Line Key Template.")
def create(
    template_name: str = typer.Option(None, "--template-name", help="(required) Name of the Line Key Template."),
    device_model: str = typer.Option(None, "--device-model", help="(required) The model of the device for which the Line Key Template is applicable. The corresponding device model display name sometimes called the product name, can also be used to specify the model."),
    user_reorder_enabled: bool = typer.Option(None, "--user-reorder-enabled/--no-user-reorder-enabled", help="User Customization Enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Line Key Template.\n\n\b\nExample: wxcli device-settings create --template-name TEMPLATE_NAME --device-model DEVICE_MODEL\n\n\b\nExample --json-body: '{"templateName":"...","deviceModel":"...","lineKeys":[{"lineKeyIndex":"...","lineKeyType":"...","sharedLineIndex":"...","lineKeyLabel":"...","lineKeyValue":"..."}],"userReorderEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/lineKeyTemplates"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if template_name is not None:
            body["templateName"] = template_name
        if device_model is not None:
            body["deviceModel"] = device_model
        if user_reorder_enabled is not None:
            body["userReorderEnabled"] = user_reorder_enabled
        _missing = [f for f in ['templateName', 'deviceModel'] if f not in body or body[f] is None]
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



@app.command("show-line-key-templates", short_help="Get details of a Line Key Template.")
def show_line_key_templates(
    template_id: str = typer.Argument(help="Webex DEVICE_LINE_KEY_TEMPLATE id, from: wxcli device-settings list-line-key-templates"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get details of a Line Key Template.\n\n\b\nExample: wxcli device-settings show-line-key-templates TEMPLATE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/lineKeyTemplates/{template_id}"
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



_BODY_SKELETON_UPDATE_LINE_KEY_TEMPLATES = '{"lineKeys":[{"lineKeyIndex":"...","lineKeyType":"...","sharedLineIndex":"...","lineKeyLabel":"...","lineKeyValue":"..."}],"userReorderEnabled":true}'

@app.command("update-line-key-templates", short_help="Modify a Line Key Template.")
def update_line_key_templates(
    template_id: str = typer.Argument(help="Webex DEVICE_LINE_KEY_TEMPLATE id, from: wxcli device-settings list-line-key-templates"),
    user_reorder_enabled: bool = typer.Option(None, "--user-reorder-enabled/--no-user-reorder-enabled", help="Indicates whether the user can reorder the line keys."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Line Key Template.\n\n\b\nExample: wxcli device-settings update-line-key-templates TEMPLATE_ID\n\n\b\nExample --json-body: '{"lineKeys":[{"lineKeyIndex":"...","lineKeyType":"...","sharedLineIndex":"...","lineKeyLabel":"...","lineKeyValue":"..."}],"userReorderEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_LINE_KEY_TEMPLATES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/lineKeyTemplates/{template_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if user_reorder_enabled is not None:
            body["userReorderEnabled"] = user_reorder_enabled
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
        emit({"status": "updated", "id": template_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Line Key Template.")
def delete(
    template_id: str = typer.Argument(help="Webex DEVICE_LINE_KEY_TEMPLATE id, from: wxcli device-settings list-line-key-templates"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Line Key Template.\n\n\b\nExample: wxcli device-settings delete TEMPLATE_ID"""
    if not force:
        typer.confirm(f"Delete {template_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/lineKeyTemplates/{template_id}"
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
        typer.echo(f"Deleted: {template_id}")
    else:
        emit({"status": "deleted", "id": template_id}, output=output, fields=fields)



_BODY_SKELETON_PREVIEW_APPLY_LINE = '{"action":"APPLY_TEMPLATE","templateId":"...","locationIds":["..."],"excludeDevicesWithCustomLayout":true,"includeDeviceTags":["..."],"excludeDeviceTags":["..."],"advisoryTypes":{"moreSharedAppearancesEnabled":true,"fewSharedAppearancesEnabled":true,"moreMonitorAppearancesEnabled":true,"moreCPEAppearancesEnabled":true,"moreModeManagementAppearancesEnabled":true}}'

@app.command("preview-apply-line", short_help="Preview Apply Line Key Template.")
def preview_apply_line(
    action: str = typer.Option(None, "--action", help="Choices: APPLY_TEMPLATE, APPLY_DEFAULT_TEMPLATES"),
    template_id: str = typer.Option(None, "--template-id", help="`templateId` is required for `APPLY_TEMPLATE` action."),
    exclude_devices_with_custom_layout: str = typer.Option(None, "--exclude-devices-with-custom-layout", help="Indicates whether to exclude devices with custom layout."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Preview Apply Line Key Template.\n\n\b\nExample: wxcli device-settings preview-apply-line --action APPLY_TEMPLATE --template-id TEMPLATE_ID\n\n\b\nExample --json-body: '{"action":"APPLY_TEMPLATE","templateId":"...","locationIds":["..."],"excludeDevicesWithCustomLayout":true,"includeDeviceTags":["..."],"excludeDeviceTags":["..."],"advisoryTypes":{"moreSharedAppearancesEnabled":true,"fewSharedAppearancesEnabled":true,"moreMonitorAppearancesEnabled":true,"moreCPEAppearancesEnabled":true,"moreModeManagementAppearancesEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_PREVIEW_APPLY_LINE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/actions/previewApplyLineKeyTemplate/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if action is not None:
            body["action"] = action
        if template_id is not None:
            body["templateId"] = template_id
        if exclude_devices_with_custom_layout is not None:
            body["excludeDevicesWithCustomLayout"] = exclude_devices_with_custom_layout
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-apply-line-key-template", short_help="Get List of Apply Line Key Template jobs.")
def list_apply_line_key_template(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of Apply Line Key Template jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/applyLineKeyTemplate"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Status', 'latestExecutionStatus')], limit=limit)



_BODY_SKELETON_CREATE_APPLY_LINE_KEY_TEMPLATE = '{"action":"APPLY_TEMPLATE","templateId":"...","locationIds":["..."],"excludeDevicesWithCustomLayout":true,"includeDeviceTags":["..."],"excludeDeviceTags":["..."],"advisoryTypes":{"moreSharedAppearancesEnabled":true,"fewSharedAppearancesEnabled":true,"moreMonitorAppearancesEnabled":true,"moreCPEAppearancesEnabled":true,"moreModeManagementAppearancesEnabled":true}}'

@app.command("create-apply-line-key-template", short_help="Apply a Line Key Template.")
def create_apply_line_key_template(
    action: str = typer.Option(None, "--action", help="(required) Choices: APPLY_TEMPLATE, APPLY_DEFAULT_TEMPLATES"),
    template_id: str = typer.Option(None, "--template-id", help="(required) `templateId` is required for `APPLY_TEMPLATE` action."),
    exclude_devices_with_custom_layout: bool = typer.Option(None, "--exclude-devices-with-custom-layout/--no-exclude-devices-with-custom-layout", help="Indicates whether to exclude devices with custom layout."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Apply a Line Key Template.\n\n\b\nExample: wxcli device-settings create-apply-line-key-template --action APPLY_TEMPLATE --template-id TEMPLATE_ID\n\n\b\nExample --json-body: '{"action":"APPLY_TEMPLATE","templateId":"...","locationIds":["..."],"excludeDevicesWithCustomLayout":true,"includeDeviceTags":["..."],"excludeDeviceTags":["..."],"advisoryTypes":{"moreSharedAppearancesEnabled":true,"fewSharedAppearancesEnabled":true,"moreMonitorAppearancesEnabled":true,"moreCPEAppearancesEnabled":true,"moreModeManagementAppearancesEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_APPLY_LINE_KEY_TEMPLATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/applyLineKeyTemplate"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if action is not None:
            body["action"] = action
        if template_id is not None:
            body["templateId"] = template_id
        if exclude_devices_with_custom_layout is not None:
            body["excludeDevicesWithCustomLayout"] = exclude_devices_with_custom_layout
        _missing = [f for f in ['action', 'templateId'] if f not in body or body[f] is None]
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



@app.command("show-apply-line-key-template", short_help="Get the job status of an Apply Line Key Template job.")
def show_apply_line_key_template(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli device-settings list-apply-line-key-template"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the job status of an Apply Line Key Template job.\n\n\b\nExample: wxcli device-settings show-apply-line-key-template JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/applyLineKeyTemplate/{job_id}"
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



@app.command("show-errors", short_help="Get job errors for an Apply Line Key Template job.")
def show_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli device-settings list-apply-line-key-template"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get job errors for an Apply Line Key Template job.\n\n\b\nExample: wxcli device-settings show-errors JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/applyLineKeyTemplate/{job_id}/errors"
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



@app.command("list-supported-devices-dects", short_help="Read the DECT device type list - Deprecated.")
def list_supported_devices_dects(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the DECT device type list - Deprecated."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/dects/supportedDevices"
    params = {}
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
            items = result.get("devices", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            if "max" not in params:
                params["max"] = 1000
            items = list(api.session.follow_pagination(url=url, params=params, item_key="devices"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Model', 'model'), ('Display Name', 'displayName'), ('Base Stations', 'numberOfBaseStations')], limit=limit)



@app.command("list-supported-devices-dect-networks", short_help="Read the DECT device type list.")
def list_supported_devices_dect_networks(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the DECT device type list."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/dectNetworks/supportedDevices"
    params = {}
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
            items = result.get("devices", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            if "max" not in params:
                params["max"] = 1000
            items = list(api.session.follow_pagination(url=url, params=params, item_key="devices"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Model', 'model'), ('Display Name', 'displayName'), ('Base Stations', 'numberOfBaseStations')], limit=limit)



_BODY_SKELETON_VALIDATE_A_LIST = '{"macs":["..."]}'

@app.command("validate-a-list", short_help="Validate a list of MAC address.")
def validate_a_list(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate a list of MAC address.\n\n\b\nExample --json-body: '{"macs":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_A_LIST), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/actions/validateMacs/invoke"
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



@app.command("list-call-device-settings", short_help="List Change Device Settings Jobs.")
def list_call_device_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Change Device Settings Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/callDeviceSettings"
    params = {}
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
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Tracking ID', 'trackingId'), ('Source User ID', 'sourceUserId'), ('Source Customer ID', 'sourceCustomerId'), ('Target Customer ID', 'targetCustomerId')], limit=limit)



_BODY_SKELETON_CREATE_CALL_DEVICE_SETTINGS = '{"locationId":"...","locationCustomizationsEnabled":true,"customizations":{"ata":{"audioCodecPriority":"...","ataDtmfMode":"...","ataDtmfMethod":"...","cdpEnabled":"...","lldpEnabled":"...","qosEnabled":"...","vlan":"...","webAccessEnabled":"..."},"dect":{"audioCodecPriority":"...","cdpEnabled":"...","dect6825HandsetEmergencyNumber":"...","lldpEnabled":"...","multicast":"...","qosEnabled":"...","vlan":"...","webAccessEnabled":"..."},"mpp":{"pnacEnabled":"...","audioCodecPriority":"...","backlightTimer":"...","background":"...","cdpEnabled":"...","defaultLoggingLevel":"...","dndServicesEnabled":"...","acd":"..."},"wifi":{"audioCodecPriority":"...","ldap":"...","webAccess":"...","phoneSecurityPwd":"..."}}}'

@app.command("create-call-device-settings", short_help="Change Device Settings Across Organization Or Location Job.")
def create_call_device_settings(
    location_id: str = typer.Option(None, "--location-id", help="Location within an organization where changes of device setings will be applied to all the devices within it."),
    location_customizations_enabled: bool = typer.Option(None, "--location-customizations-enabled/--no-location-customizations-enabled", help="Indicates if all the devices within this location will be customized with new requested customizations(if set to `true`) or will be overridden with the one at organization level (if set to `false` or any other value). This field has no effect when the job is being triggered at organization level."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Change Device Settings Across Organization Or Location Job.\n\n\b\nExample --json-body: '{"locationId":"...","locationCustomizationsEnabled":true,"customizations":{"ata":{"audioCodecPriority":"...","ataDtmfMode":"...","ataDtmfMethod":"...","cdpEnabled":"...","lldpEnabled":"...","qosEnabled":"...","vlan":"...","webAccessEnabled":"..."},"dect":{"audioCodecPriority":"...","cdpEnabled":"...","dect6825HandsetEmergencyNumber":"...","lldpEnabled":"...","multicast":"...","qosEnabled":"...","vlan":"...","webAccessEnabled":"..."},"mpp":{"pnacEnabled":"...","audioCodecPriority":"...","backlightTimer":"...","background":"...","cdpEnabled":"...","defaultLoggingLevel":"...","dndServicesEnabled":"...","acd":"..."},"wifi":{"audioCodecPriority":"...","ldap":"...","webAccess":"...","phoneSecurityPwd":"..."}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CALL_DEVICE_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/callDeviceSettings"
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
        if location_customizations_enabled is not None:
            body["locationCustomizationsEnabled"] = location_customizations_enabled
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



@app.command("show-call-device-settings", short_help="Get Change Device Settings Job Status.")
def show_call_device_settings(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli device-settings list-call-device-settings"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Change Device Settings Job Status.\n\n\b\nExample: wxcli device-settings show-call-device-settings JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/callDeviceSettings/{job_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-errors-call-device-settings", short_help="List Change Device Settings Job Errors.")
def list_errors_call_device_settings(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli device-settings list-call-device-settings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Change Device Settings Job Errors.\n\n\b\nExample: wxcli device-settings list-errors-call-device-settings JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/callDeviceSettings/{job_id}/errors"
    params = {}
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
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Tracking ID', 'trackingId'), ('Item', 'item'), ('Item Number', 'itemNumber')], limit=limit)



@app.command("list-layout", short_help="Get Device Layout by Device ID.")
def list_layout(
    device_id: str = typer.Argument(help="Webex DEVICE id, from: wxcli devices list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Layout by Device ID.\n\n\b\nExample: wxcli device-settings list-layout DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/layout"
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
    items = result.get("lineKeys", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Line Key Index', 'lineKeyIndex'), ('Line Key Type', 'lineKeyType'), ('Line Key Label', 'lineKeyLabel'), ('Line Key Value', 'lineKeyValue'), ('Shared Line Index', 'sharedLineIndex')], limit=limit)



_BODY_SKELETON_UPDATE_LAYOUT = '{"layoutMode":"DEFAULT","lineKeys":[{"lineKeyIndex":"...","lineKeyType":"...","sharedLineIndex":"...","lineKeyLabel":"...","lineKeyValue":"..."}],"userReorderEnabled":true,"kemModuleType":"KEM_14_KEYS","kemKeys":[{"kemModuleIndex":"...","kemKeyIndex":"...","kemKeyType":"...","sharedLineIndex":"...","kemKeyLabel":"...","kemKeyValue":"..."}]}'

@app.command("update-layout", short_help="Modify Device Layout by Device ID.")
def update_layout(
    device_id: str = typer.Argument(help="Webex DEVICE id, from: wxcli devices list"),
    layout_mode: str = typer.Option(None, "--layout-mode", help="Choices: DEFAULT, CUSTOM"),
    user_reorder_enabled: bool = typer.Option(None, "--user-reorder-enabled/--no-user-reorder-enabled", help="If `true`, user customization is enabled."),
    kem_module_type: str = typer.Option(None, "--kem-module-type", help="Choices: KEM_14_KEYS, KEM_18_KEYS, KEM_20_KEYS"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Device Layout by Device ID.\n\n\b\nExample: wxcli device-settings update-layout DEVICE_ID --layout-mode DEFAULT\n\n\b\nExample --json-body: '{"layoutMode":"DEFAULT","lineKeys":[{"lineKeyIndex":"...","lineKeyType":"...","sharedLineIndex":"...","lineKeyLabel":"...","lineKeyValue":"..."}],"userReorderEnabled":true,"kemModuleType":"KEM_14_KEYS","kemKeys":[{"kemModuleIndex":"...","kemKeyIndex":"...","kemKeyType":"...","sharedLineIndex":"...","kemKeyLabel":"...","kemKeyValue":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_LAYOUT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/layout"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if layout_mode is not None:
            body["layoutMode"] = layout_mode
        if user_reorder_enabled is not None:
            body["userReorderEnabled"] = user_reorder_enabled
        if kem_module_type is not None:
            body["kemModuleType"] = kem_module_type
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
        emit({"status": "updated", "id": device_id}, output=output, fields=fields)



@app.command("list-rebuild-phones", short_help="List Rebuild Phones Jobs.")
def list_rebuild_phones(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Rebuild Phones Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/rebuildPhones"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Status', 'latestExecutionStatus')], limit=limit)



_BODY_SKELETON_CREATE_REBUILD_PHONES = '{"locationId":"..."}'

@app.command("create-rebuild-phones", short_help="Rebuild Phones Configuration.")
def create_rebuild_phones(
    location_id: str = typer.Option(None, "--location-id", help="(required) Unique identifier of the location."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Rebuild Phones Configuration.\n\n\b\nExample: wxcli device-settings create-rebuild-phones --location-id LOCATION_ID\n\n\b\nExample --json-body: '{"locationId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_REBUILD_PHONES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/rebuildPhones"
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



@app.command("show-rebuild-phones", short_help="Get the Job Status of a Rebuild Phones Job.")
def show_rebuild_phones(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli device-settings list-rebuild-phones"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Job Status of a Rebuild Phones Job.\n\n\b\nExample: wxcli device-settings show-rebuild-phones JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/rebuildPhones/{job_id}"
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



@app.command("list-errors-rebuild-phones", short_help="Get Job Errors for a Rebuild Phones Job.")
def list_errors_rebuild_phones(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli device-settings list-rebuild-phones"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Job Errors for a Rebuild Phones Job.\n\n\b\nExample: wxcli device-settings list-errors-rebuild-phones JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/rebuildPhones/{job_id}/errors"
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



@app.command("show-settings-devices-3", short_help="Get Device Settings for a Person.")
def show_settings_devices_3(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Settings for a Person.\n\n\b\nExample: wxcli device-settings show-settings-devices-3 PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/devices/settings"
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



_BODY_SKELETON_UPDATE_SETTINGS_DEVICES_1 = '{"compression":"ON"}'

@app.command("update-settings-devices-1", short_help="Update Device Settings for a Person.")
def update_settings_devices_1(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    compression: str = typer.Option(None, "--compression", help="Choices: ON, OFF"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Settings for a Person.\n\n\b\nExample: wxcli device-settings update-settings-devices-1 PERSON_ID --compression ON\n\n\b\nExample --json-body: '{"compression":"ON"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS_DEVICES_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/devices/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if compression is not None:
            body["compression"] = compression
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



@app.command("show-settings-devices-4", short_help="Get Device Settings for a Workspace.")
def show_settings_devices_4(
    workspace_id: str = typer.Argument(help="Webex PLACE id, from: wxcli workspaces list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Settings for a Workspace.\n\n\b\nExample: wxcli device-settings show-settings-devices-4 WORKSPACE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/devices/settings"
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



_BODY_SKELETON_UPDATE_SETTINGS_DEVICES_2 = '{"compression":"ON"}'

@app.command("update-settings-devices-2", short_help="Update Device Settings for a Workspace.")
def update_settings_devices_2(
    workspace_id: str = typer.Argument(help="Webex PLACE id, from: wxcli workspaces list"),
    compression: str = typer.Option(None, "--compression", help="Choices: ON, OFF"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Settings for a Workspace.\n\n\b\nExample: wxcli device-settings update-settings-devices-2 WORKSPACE_ID --compression ON\n\n\b\nExample --json-body: '{"compression":"ON"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS_DEVICES_2), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/devices/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if compression is not None:
            body["compression"] = compression
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
        emit({"status": "updated", "id": workspace_id}, output=output, fields=fields)



@app.command("list-background-images", short_help="Read the List of Background Images.")
def list_background_images(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Background Images."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/backgroundImages"
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
    items = result.get("backgroundImages", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('File Name', 'fileName'), ('Background Image URL', 'backgroundImageUrl')], limit=limit)



_BODY_SKELETON_DELETE_BACKGROUND_IMAGES = '{"backgroundImages":[{"fileName":"...","forceDelete":"..."}]}'

@app.command("delete-background-images", short_help="Delete Device Background Images.")
def delete_background_images(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Device Background Images.\n\n\b\nExample --json-body: '{"backgroundImages":[{"fileName":"...","forceDelete":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE_BACKGROUND_IMAGES), indent=2))
        raise typer.Exit(0)
    if not force:
        typer.confirm("Delete this resource?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/backgroundImages"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    missing = [f for f in ['backgroundImages'] if f not in body]
    if missing:
        typer.echo(f"Error: required body field(s) missing: {', '.join(missing)}. Pass them via --json-body — this delete needs to know what to delete.", err=True)
        raise typer.Exit(1)
    try:
        result = api.session.rest_delete(url, json=body or None, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo("Deleted.")
    else:
        emit({"status": "deleted"}, output=output, fields=fields)



@app.command("show-count-devices", short_help="Get User Devices Count.")
def show_count_devices(
    person_id: str = typer.Argument(help="Webex PERSON id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User Devices Count.\n\n\b\nExample: wxcli device-settings show-count-devices PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/devices/count"
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


