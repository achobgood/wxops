import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling virtual-line-settings.")


@app.command("list", short_help="Read the List of Virtual Lines.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of virtual lines matching these location ids. Example for multiple values - `?locationId=locId1&locationId=locId2`."),
    id_param: str = typer.Option(None, "--id", help="Return the list of virtual lines matching these virtualLineIds. Example for multiple values - `?id=id1&id=id2`."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of virtual lines matching these owner names. Example for multiple values - `?ownerName=name1&ownerName=name2`."),
    phone_number: str = typer.Option(None, "--phone-number", help="Return the list of virtual lines matching these phone numbers. Example for multiple values - `?phoneNumber=number1&phoneNumber=number2`."),
    location_name: str = typer.Option(None, "--location-name", help="Return the list of virtual lines matching the location names. Example for multiple values - `?locationName=loc1&locationName=loc2`."),
    order: str = typer.Option(None, "--order", help="Return the list of virtual lines based on the order. Default sort will be in an Ascending order. Maximum 3 orders allowed at a time. Example for multiple values - `?order=order1&order=order2`."),
    has_device_assigned: str = typer.Option(None, "--has-device-assigned", help="If `true`, includes only virtual lines with devices assigned. When not explicitly specified, the default includes both virtual lines with devices assigned and not assigned."),
    has_extension_assigned: str = typer.Option(None, "--has-extension-assigned", help="If `true`, includes only virtual lines with an extension assigned. When not explicitly specified, the default includes both virtual lines with extension assigned and not assigned."),
    has_dn_assigned: str = typer.Option(None, "--has-dn-assigned", help="If `true`, includes only virtual lines with an assigned directory number, also known as a Dn. When not explicitly specified, the default includes both virtual lines with a Dn assigned and not assigned."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Virtual Lines."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if id_param is not None:
        params["id"] = id_param
    if owner_name is not None:
        params["ownerName"] = owner_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if location_name is not None:
        params["locationName"] = location_name
    if order is not None:
        params["order"] = order
    if has_device_assigned is not None:
        params["hasDeviceAssigned"] = has_device_assigned
    if has_extension_assigned is not None:
        params["hasExtensionAssigned"] = has_extension_assigned
    if has_dn_assigned is not None:
        params["hasDnAssigned"] = has_dn_assigned
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
            items = result.get("virtualLines", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="virtualLines"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Caller ID Last Name', 'callerIdLastName'), ('Caller ID First Name', 'callerIdFirstName')], limit=limit)



_BODY_SKELETON_CREATE = '{"firstName":"...","lastName":"...","locationId":"...","displayName":"...","phoneNumber":"...","extension":"...","callerIdLastName":"...","callerIdFirstName":"...","callerIdNumber":"..."}'

@app.command("create", short_help="Create a Virtual Line.")
def create(
    first_name: str = typer.Option(None, "--first-name", help="(required) First name defined for a virtual line. Minimum length is 1. Maximum length is 30."),
    last_name: str = typer.Option(None, "--last-name", help="(required) Last name defined for a virtual line. Minimum length is 1. Maximum length is 30."),
    display_name: str = typer.Option(None, "--display-name", help="Display name defined for a virtual line."),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number of a virtual line. Minimum length is 1. Maximum length is 23. Either `phoneNumber` or `extension` is mandatory."),
    extension: str = typer.Option(None, "--extension", help="Extension of a virtual line. Minimum length is 2. Maximum length is 10. Either `phoneNumber` or `extension` is mandatory."),
    location_id: str = typer.Option(None, "--location-id", help="(required) ID of location for virtual line."),
    caller_id_last_name: str = typer.Option(None, "--caller-id-last-name", help="Last name used in the Calling Line ID and for dial-by-name functions. Minimum length is 1. Maximum length is 30."),
    caller_id_first_name: str = typer.Option(None, "--caller-id-first-name", help="First name used in the Calling Line ID and for dial-by-name functions. Minimum length is 1. Maximum length is 30."),
    caller_id_number: str = typer.Option(None, "--caller-id-number", help="Phone number to appear as the CLID for all calls. Minimum length is 1. Maximum length is 23."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings create --first-name FIRST_NAME --last-name LAST_NAME --location-id LOCATION_ID\n\n\b\nExample --json-body: '{"firstName":"...","lastName":"...","locationId":"...","displayName":"...","phoneNumber":"...","extension":"...","callerIdLastName":"...","callerIdFirstName":"...","callerIdNumber":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if display_name is not None:
            body["displayName"] = display_name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if location_id is not None:
            body["locationId"] = location_id
        if caller_id_last_name is not None:
            body["callerIdLastName"] = caller_id_last_name
        if caller_id_first_name is not None:
            body["callerIdFirstName"] = caller_id_first_name
        if caller_id_number is not None:
            body["callerIdNumber"] = caller_id_number
        _missing = [f for f in ['firstName', 'lastName', 'locationId'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Read Call Recording Settings for a Virtual Line.")
def show(
    virtual_line_id: str = typer.Argument(help="UUID, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Recording Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callRecording"
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



_BODY_SKELETON_UPDATE = '{"enabled":true,"record":"Always","recordVoicemailEnabled":true,"notification":{"type":"Beep","enabled":true},"repeat":{"interval":0,"enabled":true},"startStopAnnouncement":{"internalCallsEnabled":true,"pstnCallsEnabled":true}}'

@app.command("update", short_help="Configure Call Recording Settings for a Virtual Line.")
def update(
    virtual_line_id: str = typer.Argument(help="UUID, from: wxcli virtual-line-settings list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if call recording is enabled."),
    record: str = typer.Option(None, "--record", help="Choices: Always, Never, Always with Pause/Resume, On Demand with User Initiated Start"),
    record_voicemail_enabled: bool = typer.Option(None, "--record-voicemail-enabled/--no-record-voicemail-enabled", help="When `true`, voicemail messages are also recorded."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Recording Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"enabled":true,"record":"Always","recordVoicemailEnabled":true,"notification":{"type":"Beep","enabled":true},"repeat":{"interval":0,"enabled":true},"startStopAnnouncement":{"internalCallsEnabled":true,"pstnCallsEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callRecording"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-virtual-lines", short_help="Get Details for a Virtual Line.")
def show_virtual_lines(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-virtual-lines VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}"
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



_BODY_SKELETON_UPDATE_VIRTUAL_LINES = '{"firstName":"...","lastName":"...","displayName":"...","phoneNumber":"...","extension":"...","announcementLanguage":"...","callerIdLastName":"...","callerIdFirstName":"...","callerIdNumber":"...","timeZone":"..."}'

@app.command("update-virtual-lines", short_help="Update a Virtual Line.")
def update_virtual_lines(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    first_name: str = typer.Option(None, "--first-name", help="First name defined for a virtual line. Minimum length is 1. Maximum length is 64."),
    last_name: str = typer.Option(None, "--last-name", help="Last name defined for a virtual line. Minimum length is 1. Maximum length is 64."),
    display_name: str = typer.Option(None, "--display-name", help="Display name defined for a virtual line."),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number of a virtual line. Minimum length is 1. Maximum length is 23. Either `phoneNumber` or `extension` is mandatory."),
    extension: str = typer.Option(None, "--extension", help="Extension of a virtual line. Minimum length is 2. Maximum length is 10. Either `phoneNumber` or `extension` is mandatory."),
    announcement_language: str = typer.Option(None, "--announcement-language", help="Virtual Line's announcement language."),
    caller_id_last_name: str = typer.Option(None, "--caller-id-last-name", help="Last name used in the Calling Line ID and for dial-by-name functions. Minimum length is 1. Maximum length is 64."),
    caller_id_first_name: str = typer.Option(None, "--caller-id-first-name", help="First name used in the Calling Line ID and for dial-by-name functions. Minimum length is 1. Maximum length is 128."),
    caller_id_number: str = typer.Option(None, "--caller-id-number", help="Phone number to appear as the CLID for all calls. Minimum length is 1. Maximum length is 23."),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone defined for the virtual line."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-virtual-lines VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"firstName":"...","lastName":"...","displayName":"...","phoneNumber":"...","extension":"...","announcementLanguage":"...","callerIdLastName":"...","callerIdFirstName":"...","callerIdNumber":"...","timeZone":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VIRTUAL_LINES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if display_name is not None:
            body["displayName"] = display_name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if announcement_language is not None:
            body["announcementLanguage"] = announcement_language
        if caller_id_last_name is not None:
            body["callerIdLastName"] = caller_id_last_name
        if caller_id_first_name is not None:
            body["callerIdFirstName"] = caller_id_first_name
        if caller_id_number is not None:
            body["callerIdNumber"] = caller_id_number
        if time_zone is not None:
            body["timeZone"] = time_zone
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Virtual Line.")
def delete(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings delete VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {virtual_line_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}"
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
        typer.echo(f"Deleted: {virtual_line_id}")
    else:
        emit({"status": "deleted", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-number", short_help="Get Phone Number assigned for a Virtual Line.")
def show_number(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Phone Number assigned for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-number VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/number"
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



_BODY_SKELETON_UPDATE_DIRECTORY_SEARCH = '{"enabled":true}'

@app.command("update-directory-search", short_help="Update Directory search for a Virtual Line.")
def update_directory_search(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not the directory search for a virtual line is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Directory search for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-directory-search VIRTUAL_LINE_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DIRECTORY_SEARCH), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/directorySearch"
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
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("list-devices", short_help="Get List of Devices assigned for a Virtual Line.")
def list_devices(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of Devices assigned for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings list-devices VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/devices"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Model', 'model'), ('MAC', 'mac'), ('Primary Owner', 'primaryOwner'), ('Type', 'type')], limit=limit)



@app.command("list-dect-networks", short_help="Get List of DECT Networks Handsets for a Virtual Line.")
def list_dect_networks(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of DECT Networks Handsets for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings list-dect-networks VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/dectNetworks"
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
    items = result.get("dectNetworks", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Primary Enabled', 'primaryEnabled'), ('Number Of Handsets Assigned', 'numberOfHandsetsAssigned')], limit=limit)



@app.command("list-caller-id", short_help="Read Caller ID Settings for a Virtual Line.")
def list_caller_id(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Caller ID Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings list-caller-id VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callerId"
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



_BODY_SKELETON_UPDATE_CALLER_ID_VIRTUAL_LINES = '{"selected":"DIRECT_LINE","customNumber":"...","firstName":"...","lastName":"...","blockInForwardCallsEnabled":true,"externalCallerIdNamePolicy":"DIRECT_LINE","customExternalCallerIdName":"...","additionalExternalCallerIdDirectLineEnabled":true,"additionalExternalCallerIdLocationNumberEnabled":true,"additionalExternalCallerIdCustomNumber":"...","directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByFirstName":"...","dialByLastName":"..."}'

@app.command("update-caller-id-virtual-lines", short_help="Configure Caller ID Settings for a Virtual Line.")
def update_caller_id_virtual_lines(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
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
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Caller ID Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-caller-id-virtual-lines VIRTUAL_LINE_ID --selected DIRECT_LINE\n\n\b\nExample --json-body: '{"selected":"DIRECT_LINE","customNumber":"...","firstName":"...","lastName":"...","blockInForwardCallsEnabled":true,"externalCallerIdNamePolicy":"DIRECT_LINE","customExternalCallerIdName":"...","additionalExternalCallerIdDirectLineEnabled":true,"additionalExternalCallerIdLocationNumberEnabled":true,"additionalExternalCallerIdCustomNumber":"...","directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByFirstName":"...","dialByLastName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALLER_ID_VIRTUAL_LINES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callerId"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-call-waiting", short_help="Read Call Waiting Settings for a Virtual Line.")
def show_call_waiting(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Waiting Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-call-waiting VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callWaiting"
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

@app.command("update-call-waiting", short_help="Configure Call Waiting Settings for a Virtual Line.")
def update_call_waiting(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Call Waiting feature is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Waiting Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-call-waiting VIRTUAL_LINE_ID --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_WAITING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callWaiting"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-call-forwarding", short_help="Read Call Forwarding Settings for a Virtual Line.")
def show_call_forwarding(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Forwarding Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-call-forwarding VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callForwarding"
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

@app.command("update-call-forwarding", short_help="Configure Call Forwarding Settings for a Virtual Line.")
def update_call_forwarding(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Forwarding Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-call-forwarding VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"busy":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true},"noAnswer":{"enabled":true,"destination":"...","numberOfRings":0,"destinationVoicemailEnabled":true}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_FORWARDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callForwarding"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-incoming-permission", short_help="Read Incoming Permission Settings for a Virtual Line.")
def show_incoming_permission(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Incoming Permission Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-incoming-permission VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/incomingPermission"
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

@app.command("update-incoming-permission", short_help="Configure Incoming Permission Settings for a Virtual Line.")
def update_incoming_permission(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help="When true, indicates that this virtual line uses the specified calling permissions for receiving inbound calls rather than the organizational defaults."),
    external_transfer: str = typer.Option(None, "--external-transfer", help="Choices: ALLOW_ALL_EXTERNAL, ALLOW_ONLY_TRANSFERRED_EXTERNAL, BLOCK_ALL_EXTERNAL"),
    internal_calls_enabled: bool = typer.Option(None, "--internal-calls-enabled/--no-internal-calls-enabled", help="Internal calls are allowed to be received."),
    collect_calls_enabled: bool = typer.Option(None, "--collect-calls-enabled/--no-collect-calls-enabled", help="Collect calls are allowed to be received."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Incoming Permission Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-incoming-permission VIRTUAL_LINE_ID --use-custom-enabled --external-transfer ALLOW_ALL_EXTERNAL --internal-calls-enabled --collect-calls-enabled\n\n\b\nExample --json-body: '{"useCustomEnabled":true,"externalTransfer":"ALLOW_ALL_EXTERNAL","internalCallsEnabled":true,"collectCallsEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_INCOMING_PERMISSION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/incomingPermission"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("list-outgoing-permission", short_help="Retrieve a virtual line's Outgoing Calling Permissions Settings.")
def list_outgoing_permission(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a virtual line's Outgoing Calling Permissions Settings.\n\n\b\nExample: wxcli virtual-line-settings list-outgoing-permission VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission"
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

@app.command("update-outgoing-permission", short_help="Modify a virtual line's Outgoing Calling Permissions Settings.")
def update_outgoing_permission(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help="When true, indicates that this user uses the shared control that applies to all outgoing call settings categories when placing outbound calls."),
    use_custom_permissions: bool = typer.Option(None, "--use-custom-permissions/--no-use-custom-permissions", help="When true, indicates that this user uses the specified outgoing calling permissions when placing outbound calls."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a virtual line's Outgoing Calling Permissions Settings.\n\n\b\nExample: wxcli virtual-line-settings update-outgoing-permission VIRTUAL_LINE_ID --json-body '{"callingPermissions":[{"transferEnabled":true}]}'\n\n\b\nExample --json-body: '{"callingPermissions":[{"transferEnabled":true,"callType":"INTERNAL_CALL","action":"ALLOW"}],"useCustomEnabled":true,"useCustomPermissions":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_OUTGOING_PERMISSION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("list-access-codes", short_help="Retrieve Access Codes for a Virtual Line.")
def list_access_codes(
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Access Codes for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings list-access-codes VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/accessCodes"
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

@app.command("create-access-codes", short_help="Create Access Codes for a Virtual Line.")
def create_access_codes(
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    code: str = typer.Option(None, "--code", help="(required) An Access code."),
    description: str = typer.Option(None, "--description", help="(required) The description of the access code."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Access Codes for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings create-access-codes VIRTUAL_LINE_ID --code CODE --description DESCRIPTION\n\n\b\nExample --json-body: '{"code":"...","description":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ACCESS_CODES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/accessCodes"
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

@app.command("update-access-codes", short_help="Modify Access Codes for a Virtual Line.")
def update_access_codes(
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Access Codes for a Virtual Line.\n\nDESTRUCTIVE: this PUT only deletes despite the summary above. It cannot add or modify.\n\n\b\nExample: wxcli virtual-line-settings update-access-codes VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"deleteCodes":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ACCESS_CODES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/accessCodes"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted.")
    else:
        emit({"status": "deleted", "id": virtual_line_id}, output=output, fields=fields)



@app.command("delete-access-codes", short_help="Delete Access Codes for a Virtual Line.")
def delete_access_codes(
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Access Codes for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings delete-access-codes VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Access Codes for {virtual_line_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/accessCodes"
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
        typer.echo(f"Deleted: {virtual_line_id}")
    else:
        emit({"status": "deleted", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-auto-transfer-numbers", short_help="Retrieve Transfer Numbers for a Virtual Line.")
def show_auto_transfer_numbers(
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Transfer Numbers for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-auto-transfer-numbers VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/autoTransferNumbers"
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

@app.command("update-auto-transfer-numbers", short_help="Modify Transfer Numbers for a Virtual Line.")
def update_auto_transfer_numbers(
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    use_custom_transfer_numbers: bool = typer.Option(None, "--use-custom-transfer-numbers/--no-use-custom-transfer-numbers", help="When `true`, use custom settings for the transfer numbers category of outbound permissions."),
    auto_transfer_number1: str = typer.Option(None, "--auto-transfer-number1", help="When calling a specific call type, this workspace will be automatically transferred to another number."),
    auto_transfer_number2: str = typer.Option(None, "--auto-transfer-number2", help="When calling a specific call type, this workspace will be automatically transferred to another number."),
    auto_transfer_number3: str = typer.Option(None, "--auto-transfer-number3", help="When calling a specific call type, this workspace will be automatically transferred to another number."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Transfer Numbers for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-auto-transfer-numbers VIRTUAL_LINE_ID --use-custom-transfer-numbers\n\n\b\nExample --json-body: '{"useCustomTransferNumbers":true,"autoTransferNumber1":"...","autoTransferNumber2":"...","autoTransferNumber3":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_AUTO_TRANSFER_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/autoTransferNumbers"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("list-digit-patterns", short_help="Retrieve Digit Patterns for a Virtual Profile.")
def list_digit_patterns(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Digit Patterns for a Virtual Profile.\n\n\b\nExample: wxcli virtual-line-settings list-digit-patterns VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns"
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

@app.command("create-digit-patterns", short_help="Create Digit Pattern for a Virtual Profile.")
def create_digit_patterns(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
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
    """Create Digit Pattern for a Virtual Profile.\n\n\b\nExample: wxcli virtual-line-settings create-digit-patterns VIRTUAL_LINE_ID --name NAME --pattern PATTERN --action ALLOW --transfer-enabled\n\n\b\nExample --json-body: '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DIGIT_PATTERNS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns"
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

@app.command("update-digit-patterns-outgoing-permission", short_help="Modify the Digit Pattern Category Control Settings for a Virtual Profile.")
def update_digit_patterns_outgoing_permission(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    use_custom_digit_patterns: bool = typer.Option(None, "--use-custom-digit-patterns/--no-use-custom-digit-patterns", help="When `true`, use custom settings for the digit patterns category of outgoing call permissions."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify the Digit Pattern Category Control Settings for a Virtual Profile.\n\n\b\nExample: wxcli virtual-line-settings update-digit-patterns-outgoing-permission VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"useCustomDigitPatterns":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DIGIT_PATTERNS_OUTGOING_PERMISSION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("delete-digit-patterns-outgoing-permission", short_help="Delete all Digit Patterns for a Virtual Profile.")
def delete_digit_patterns_outgoing_permission(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete all Digit Patterns for a Virtual Profile.\n\n\b\nExample: wxcli virtual-line-settings delete-digit-patterns-outgoing-permission VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Digit Patterns for {virtual_line_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns"
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
        typer.echo(f"Deleted: {virtual_line_id}")
    else:
        emit({"status": "deleted", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-digit-patterns", short_help="Retrieve Specified Digit Pattern Details for a Virtual Profile.")
def show_digit_patterns(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli virtual-line-settings list-digit-patterns"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Specified Digit Pattern Details for a Virtual Profile.\n\n\b\nExample: wxcli virtual-line-settings show-digit-patterns VIRTUAL_LINE_ID DIGIT_PATTERN_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
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

@app.command("update-digit-patterns-outgoing-permission-1", short_help="Modify a Digit Pattern for a Virtual Profile.")
def update_digit_patterns_outgoing_permission_1(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli virtual-line-settings list-digit-patterns"),
    name: str = typer.Option(None, "--name", help="A unique name for the digit pattern."),
    pattern: str = typer.Option(None, "--pattern", help="The digit pattern to be matched with the input number."),
    action: str = typer.Option(None, "--action", help="Choices: ALLOW, BLOCK, AUTH_CODE, TRANSFER_NUMBER_1, TRANSFER_NUMBER_2, TRANSFER_NUMBER_3"),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help="If `true`, allows transfer and forwarding for the call type."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Digit Pattern for a Virtual Profile.\n\n\b\nExample: wxcli virtual-line-settings update-digit-patterns-outgoing-permission-1 VIRTUAL_LINE_ID DIGIT_PATTERN_ID\n\n\b\nExample --json-body: '{"name":"...","pattern":"...","action":"ALLOW","transferEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DIGIT_PATTERNS_OUTGOING_PERMISSION_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": digit_pattern_id}, output=output, fields=fields)



@app.command("delete-digit-patterns-outgoing-permission-1", short_help="Delete a Digit Pattern for a Virtual Profile.")
def delete_digit_patterns_outgoing_permission_1(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    digit_pattern_id: str = typer.Argument(help="Webex SCHEDULE id, from: wxcli virtual-line-settings list-digit-patterns"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Digit Pattern for a Virtual Profile.\n\n\b\nExample: wxcli virtual-line-settings delete-digit-patterns-outgoing-permission-1 VIRTUAL_LINE_ID DIGIT_PATTERN_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {digit_pattern_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
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



@app.command("show-intercept", short_help="Read Call Intercept Settings for a Virtual Line.")
def show_intercept(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Intercept Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-intercept VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/intercept"
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

@app.command("update-intercept", short_help="Configure Call Intercept Settings for a Virtual Line.")
def update_intercept(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the intercept feature is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Intercept Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-intercept VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"enabled":true,"incoming":{"type":"INTERCEPT_ALL","voicemailEnabled":true,"announcements":{"greeting":"CUSTOM","newNumber":{"enabled":true,"destination":"..."},"zeroTransfer":{"enabled":true,"destination":"..."}}},"outgoing":{"type":"INTERCEPT_ALL","transferEnabled":true,"destination":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_INTERCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/intercept"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("configure-call-intercept", short_help="Configure Call Intercept Greeting for a Virtual Line.")
def configure_call_intercept(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Intercept Greeting for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings configure-call-intercept VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/intercept/actions/announcementUpload/invoke"
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



@app.command("list-available-caller-ids", short_help="Retrieve Agent's List of Available Caller IDs.")
def list_available_caller_ids(
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Agent's List of Available Caller IDs.\n\n\b\nExample: wxcli virtual-line-settings list-available-caller-ids VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/agent/availableCallerIds"
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
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Agent's Caller ID Information.\n\n\b\nExample: wxcli virtual-line-settings show-caller-id VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/agent/callerId"
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
    virtual_line_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli virtual-line-settings list"),
    selected_caller_id: str = typer.Option(None, "--selected-caller-id", help="The unique identifier of the call queue or hunt group to use for the agent's caller ID. Set to null to use the agent's own caller ID."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Agent's Caller ID Information.\n\n\b\nExample: wxcli virtual-line-settings update-caller-id-agent VIRTUAL_LINE_ID --selected-caller-id SELECTED_CALLER_ID\n\n\b\nExample --json-body: '{"selectedCallerId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALLER_ID_AGENT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/agent/callerId"
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
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-voicemail", short_help="Read Voicemail Settings for a Virtual Line.")
def show_voicemail(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Voicemail Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-voicemail VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail"
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

@app.command("update-voicemail", short_help="Configure Voicemail Settings for a Virtual Line.")
def update_voicemail(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Voicemail is enabled or disabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Voicemail Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-voicemail VIRTUAL_LINE_ID --json-body '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."}}'\n\n\b\nExample --json-body: '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."},"faxMessage":{"enabled":true,"phoneNumber":"...","extension":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VOICEMAIL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("configure-busy-voicemail", short_help="Configure Busy Voicemail Greeting for a Virtual Line.")
def configure_busy_voicemail(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Busy Voicemail Greeting for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings configure-busy-voicemail VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail/actions/uploadBusyGreeting/invoke"
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



@app.command("configure-no-answer", short_help="Configure No Answer Voicemail Greeting for a Virtual Line.")
def configure_no_answer(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure No Answer Voicemail Greeting for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings configure-no-answer VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail/actions/uploadNoAnswerGreeting/invoke"
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



@app.command("reset-voicemail-pin", short_help="Reset Voicemail PIN for a Virtual Line.")
def reset_voicemail_pin(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reset Voicemail PIN for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings reset-voicemail-pin VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail/actions/resetPin/invoke"
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



_BODY_SKELETON_UPDATE_PASSCODE = '{"passcode":"..."}'

@app.command("update-passcode", short_help="Modify a virtual line's voicemail passcode.")
def update_passcode(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    passcode: str = typer.Option(None, "--passcode", help="Voicemail access passcode. The minimum length of the passcode is 6 and the maximum length is 30."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a virtual line's voicemail passcode.\n\n\b\nExample: wxcli virtual-line-settings update-passcode VIRTUAL_LINE_ID --passcode PASSCODE\n\n\b\nExample --json-body: '{"passcode":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PASSCODE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail/passcode"
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
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-music-on-hold", short_help="Retrieve Music On Hold Settings for a Virtual Line.")
def show_music_on_hold(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Music On Hold Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-music-on-hold VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/musicOnHold"
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

@app.command("update-music-on-hold", short_help="Configure Music On Hold Settings for a Virtual Line.")
def update_music_on_hold(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    moh_enabled: bool = typer.Option(None, "--moh-enabled/--no-moh-enabled", help="Music on hold is enabled or disabled for the workspace."),
    greeting: str = typer.Option(None, "--greeting", help="Choices: DEFAULT, CUSTOM"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Music On Hold Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-music-on-hold VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"mohEnabled":true,"greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_MUSIC_ON_HOLD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/musicOnHold"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("list-push-to-talk", short_help="Read Push-to-Talk Settings for a Virtual Line.")
def list_push_to_talk(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Push-to-Talk Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings list-push-to-talk VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/pushToTalk"
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

@app.command("update-push-to-talk", short_help="Configure Push-to-Talk Settings for a Virtual Line.")
def update_push_to_talk(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    allow_auto_answer: bool = typer.Option(None, "--allow-auto-answer/--no-allow-auto-answer", help="`true` if Push-to-Talk feature is enabled."),
    connection_type: str = typer.Option(None, "--connection-type", help="Choices: ONE_WAY, TWO_WAY"),
    access_type: str = typer.Option(None, "--access-type", help="Choices: ALLOW_MEMBERS, BLOCK_MEMBERS"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Push-to-Talk Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-push-to-talk VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"allowAutoAnswer":true,"connectionType":"ONE_WAY","accessType":"ALLOW_MEMBERS","members":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PUSH_TO_TALK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/pushToTalk"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-call-bridge", short_help="Read Call Bridge Settings for a Virtual Line.")
def show_call_bridge(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Bridge Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-call-bridge VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callBridge"
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

@app.command("update-call-bridge", short_help="Configure Call Bridge Settings for a Virtual Line.")
def update_call_bridge(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    warning_tone_enabled: bool = typer.Option(None, "--warning-tone-enabled/--no-warning-tone-enabled", help="Set to enable or disable a stutter dial tone being played to all the participants when a virtual line is bridged on the active shared line call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Bridge Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-call-bridge VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"warningToneEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_BRIDGE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callBridge"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("show-barge-in", short_help="Read Barge In Settings for a Virtual Line.")
def show_barge_in(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Barge In Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-barge-in VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/bargeIn"
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

@app.command("update-barge-in", short_help="Configure Barge In Settings for a Virtual Line.")
def update_barge_in(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Set to enable or disable the Barge In feature."),
    tone_enabled: bool = typer.Option(None, "--tone-enabled/--no-tone-enabled", help="Set to enable or disable a stutter dial tone being played when a virtual line is barging in on the active call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Barge In Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-barge-in VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"enabled":true,"toneEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_BARGE_IN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/bargeIn"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("list-privacy", short_help="Get a Virtual Line's Privacy Settings.")
def list_privacy(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Virtual Line's Privacy Settings.\n\n\b\nExample: wxcli virtual-line-settings list-privacy VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/privacy"
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

@app.command("update-privacy", short_help="Configure a Virtual Line's Privacy Settings.")
def update_privacy(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    aa_extension_dialing_enabled: bool = typer.Option(None, "--aa-extension-dialing-enabled/--no-aa-extension-dialing-enabled", help="When `true` auto attendant extension dialing is enabled."),
    aa_naming_dialing_enabled: bool = typer.Option(None, "--aa-naming-dialing-enabled/--no-aa-naming-dialing-enabled", help="When `true` auto attendant dialing by first or last name is enabled."),
    enable_phone_status_directory_privacy: bool = typer.Option(None, "--enable-phone-status-directory-privacy/--no-enable-phone-status-directory-privacy", help="When `true` phone status directory privacy is enabled."),
    enable_phone_status_pickup_barge_in_privacy: bool = typer.Option(None, "--enable-phone-status-pickup-barge-in-privacy/--no-enable-phone-status-pickup-barge-in-privacy", help="When `true` privacy is enforced for call pickup and barge-in. Only members specified by `monitoringAgents` can pickup or barge-in on the call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure a Virtual Line's Privacy Settings.\n\n\b\nExample: wxcli virtual-line-settings update-privacy VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"aaExtensionDialingEnabled":true,"aaNamingDialingEnabled":true,"enablePhoneStatusDirectoryPrivacy":true,"enablePhoneStatusPickupBargeInPrivacy":true,"monitoringAgents":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PRIVACY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/privacy"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("list-available-numbers-fax-message", short_help="Get Virtual Line Fax Message Available Phone Numbers.")
def list_available_numbers_fax_message(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_PROFILE id, from: wxcli virtual-line-settings list"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual Line Fax Message Available Phone Numbers.\n\n\b\nExample: wxcli virtual-line-settings list-available-numbers-fax-message VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/faxMessage/availableNumbers"
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-call-forwarding", short_help="Get Virtual Line Call Forward Available Phone Numbers.")
def list_available_numbers_call_forwarding(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_PROFILE id, from: wxcli virtual-line-settings list"),
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
    """Get Virtual Line Call Forward Available Phone Numbers.\n\n\b\nExample: wxcli virtual-line-settings list-available-numbers-call-forwarding VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callForwarding/availableNumbers"
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-virtual-lines", short_help="Get Virtual Line Available Phone Numbers.")
def list_available_numbers_virtual_lines(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of phone numbers for this location within the given organization. The maximum length is 36."),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual Line Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/availableNumbers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-emergency-callback-number", short_help="Get Virtual Line ECBN Available Phone Numbers.")
def list_available_numbers_emergency_callback_number(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_PROFILE id, from: wxcli virtual-line-settings list"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual Line ECBN Available Phone Numbers.\n\n\b\nExample: wxcli virtual-line-settings list-available-numbers-emergency-callback-number VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber/availableNumbers"
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-call-intercept", short_help="Get Virtual Line Call Intercept Available Phone Numbers.")
def list_available_numbers_call_intercept(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_PROFILE id, from: wxcli virtual-line-settings list"),
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
    """Get Virtual Line Call Intercept Available Phone Numbers.\n\n\b\nExample: wxcli virtual-line-settings list-available-numbers-call-intercept VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callIntercept/availableNumbers"
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("show-do-not-disturb", short_help="Retrieve DoNotDisturb Settings for a Virtual Line.")
def show_do_not_disturb(
    virtual_line_id: str = typer.Argument(help="Webex PLACE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve DoNotDisturb Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings show-do-not-disturb VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/doNotDisturb"
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



_BODY_SKELETON_UPDATE_DO_NOT_DISTURB = '{"enabled":true,"ringSplashEnabled":true}'

@app.command("update-do-not-disturb", short_help="Modify DoNotDisturb Settings for a Virtual Line.")
def update_do_not_disturb(
    virtual_line_id: str = typer.Argument(help="Webex PLACE id, from: wxcli virtual-line-settings list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the DoNotDisturb feature is enabled."),
    ring_splash_enabled: bool = typer.Option(None, "--ring-splash-enabled/--no-ring-splash-enabled", help="When `true`, enables ring reminder when you receive an incoming call while on Do Not Disturb."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify DoNotDisturb Settings for a Virtual Line.\n\n\b\nExample: wxcli virtual-line-settings update-do-not-disturb VIRTUAL_LINE_ID\n\n\b\nExample --json-body: '{"enabled":true,"ringSplashEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DO_NOT_DISTURB), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/doNotDisturb"
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
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)



@app.command("list-outbound-billing-plan", short_help="Retrieve a Virtual Line's Outbound Billing Plan.")
def list_outbound_billing_plan(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a Virtual Line's Outbound Billing Plan.\n\n\b\nExample: wxcli virtual-line-settings list-outbound-billing-plan VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outboundBillingPlan"
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



@app.command("update-outbound-billing-plan", short_help="Modify a Virtual Line's Outbound Billing Plan.")
def update_outbound_billing_plan(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Virtual Line's Outbound Billing Plan.\n\n\b\nExample: wxcli virtual-line-settings update-outbound-billing-plan VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outboundBillingPlan"
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
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)


