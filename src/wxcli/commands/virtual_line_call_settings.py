import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling virtual-line-call-settings.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of virtual lines matching these location ids"),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    id_param: str = typer.Option(None, "--id", help="Return the list of virtual lines matching these virtualLineI"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of virtual lines matching these owner names."),
    phone_number: str = typer.Option(None, "--phone-number", help="Return the list of virtual lines matching these phone number"),
    location_name: str = typer.Option(None, "--location-name", help="Return the list of virtual lines matching the location names"),
    order: str = typer.Option(None, "--order", help="Return the list of virtual lines based on the order. Default"),
    has_device_assigned: str = typer.Option(None, "--has-device-assigned", help="If `true`, includes only virtual lines with devices assigned"),
    has_extension_assigned: str = typer.Option(None, "--has-extension-assigned", help="If `true`, includes only virtual lines with an extension ass"),
    has_dn_assigned: str = typer.Option(None, "--has-dn-assigned", help="If `true`, includes only virtual lines with an assigned dire"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Virtual Lines."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("virtualLines", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    location_id: str = typer.Option(None, "--location-id", help=""),
    display_name: str = typer.Option(None, "--display-name", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    caller_id_last_name: str = typer.Option(None, "--caller-id-last-name", help=""),
    caller_id_first_name: str = typer.Option(None, "--caller-id-first-name", help=""),
    caller_id_number: str = typer.Option(None, "--caller-id-number", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if location_id is not None:
            body["locationId"] = location_id
        if display_name is not None:
            body["displayName"] = display_name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if caller_id_last_name is not None:
            body["callerIdLastName"] = caller_id_last_name
        if caller_id_first_name is not None:
            body["callerIdFirstName"] = caller_id_first_name
        if caller_id_number is not None:
            body["callerIdNumber"] = caller_id_number
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



@app.command("show")
def show(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Recording Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callRecording"
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
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    record: str = typer.Option(None, "--record", help=""),
    record_voicemail_enabled: bool = typer.Option(None, "--record-voicemail-enabled/--no-record-voicemail-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Recording Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callRecording"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if record is not None:
            body["record"] = record
        if record_voicemail_enabled is not None:
            body["recordVoicemailEnabled"] = record_voicemail_enabled
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



@app.command("delete")
def delete(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Virtual Line."""
    if not force:
        typer.confirm(f"Delete {virtual_line_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {virtual_line_id}")



@app.command("show-virtual-lines")
def show_virtual_lines(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}"
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



@app.command("update-virtual-lines")
def update_virtual_lines(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    display_name: str = typer.Option(None, "--display-name", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    announcement_language: str = typer.Option(None, "--announcement-language", help=""),
    caller_id_last_name: str = typer.Option(None, "--caller-id-last-name", help=""),
    caller_id_first_name: str = typer.Option(None, "--caller-id-first-name", help=""),
    caller_id_number: str = typer.Option(None, "--caller-id-number", help=""),
    time_zone: str = typer.Option(None, "--time-zone", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}"
    if json_body:
        body = json.loads(json_body)
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-number")
def list_number(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Phone Number assigned for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/number"
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
    items = result.get("number", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-directory-search")
def update_directory_search(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Directory search for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/directorySearch"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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



@app.command("list-devices")
def list_devices(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of Devices assigned for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/devices"
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
    items = result.get("devices", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-dect-networks")
def list_dect_networks(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of DECT Networks Handsets for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/dectNetworks"
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
    items = result.get("dectNetworks", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-caller-id")
def show_caller_id(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Caller ID Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callerId"
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



@app.command("update-caller-id-virtual-lines")
def update_caller_id_virtual_lines(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    selected: str = typer.Option(None, "--selected", help="e.g. CUSTOM"),
    custom_number: str = typer.Option(None, "--custom-number", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    block_in_forward_calls_enabled: bool = typer.Option(None, "--block-in-forward-calls-enabled/--no-block-in-forward-calls-enabled", help=""),
    external_caller_id_name_policy: str = typer.Option(None, "--external-caller-id-name-policy", help="e.g. LOCATION"),
    custom_external_caller_id_name: str = typer.Option(None, "--custom-external-caller-id-name", help=""),
    additional_external_caller_id_direct_line_enabled: bool = typer.Option(None, "--additional-external-caller-id-direct-line-enabled/--no-additional-external-caller-id-direct-line-enabled", help=""),
    additional_external_caller_id_location_number_enabled: bool = typer.Option(None, "--additional-external-caller-id-location-number-enabled/--no-additional-external-caller-id-location-number-enabled", help=""),
    additional_external_caller_id_custom_number: str = typer.Option(None, "--additional-external-caller-id-custom-number", help=""),
    dial_by_first_name: str = typer.Option(None, "--dial-by-first-name", help=""),
    dial_by_last_name: str = typer.Option(None, "--dial-by-last-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Caller ID Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callerId"
    if json_body:
        body = json.loads(json_body)
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-call-waiting")
def show_call_waiting(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Waiting Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callWaiting"
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



@app.command("update-call-waiting")
def update_call_waiting(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Waiting Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callWaiting"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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



@app.command("show-call-forwarding")
def show_call_forwarding(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Forwarding Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callForwarding"
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
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Forwarding Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callForwarding"
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



@app.command("show-incoming-permission")
def show_incoming_permission(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Incoming Permission Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/incomingPermission"
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



@app.command("update-incoming-permission")
def update_incoming_permission(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help=""),
    external_transfer: str = typer.Option(None, "--external-transfer", help="e.g. ALLOW_ONLY_TRANSFERRED_EXTERNAL"),
    internal_calls_enabled: bool = typer.Option(None, "--internal-calls-enabled/--no-internal-calls-enabled", help=""),
    collect_calls_enabled: bool = typer.Option(None, "--collect-calls-enabled/--no-collect-calls-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Incoming Permission Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/incomingPermission"
    if json_body:
        body = json.loads(json_body)
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-outgoing-permission")
def show_outgoing_permission(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a virtual line's Outgoing Calling Permissions Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission"
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



@app.command("update-outgoing-permission")
def update_outgoing_permission(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    use_custom_enabled: bool = typer.Option(None, "--use-custom-enabled/--no-use-custom-enabled", help=""),
    use_custom_permissions: bool = typer.Option(None, "--use-custom-permissions/--no-use-custom-permissions", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a virtual line's Outgoing Calling Permissions Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if use_custom_enabled is not None:
            body["useCustomEnabled"] = use_custom_enabled
        if use_custom_permissions is not None:
            body["useCustomPermissions"] = use_custom_permissions
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



@app.command("list-access-codes")
def list_access_codes(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Access Codes for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/accessCodes"
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
    items = result.get("accessCodes", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-access-codes")
def update_access_codes(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Access Codes for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/accessCodes"
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



@app.command("create-access-codes")
def create_access_codes(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    code: str = typer.Option(None, "--code", help=""),
    description: str = typer.Option(None, "--description", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Access Codes for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/accessCodes"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if code is not None:
            body["code"] = code
        if description is not None:
            body["description"] = description
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



@app.command("delete-access-codes")
def delete_access_codes(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Access Codes for a Virtual Line."""
    if not force:
        typer.confirm(f"Delete {virtual_line_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/accessCodes"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {virtual_line_id}")



@app.command("show-auto-transfer-numbers")
def show_auto_transfer_numbers(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Transfer Numbers for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/autoTransferNumbers"
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



@app.command("update-auto-transfer-numbers")
def update_auto_transfer_numbers(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    use_custom_transfer_numbers: bool = typer.Option(None, "--use-custom-transfer-numbers/--no-use-custom-transfer-numbers", help=""),
    auto_transfer_number1: str = typer.Option(None, "--auto-transfer-number1", help=""),
    auto_transfer_number2: str = typer.Option(None, "--auto-transfer-number2", help=""),
    auto_transfer_number3: str = typer.Option(None, "--auto-transfer-number3", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Transfer Numbers for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/autoTransferNumbers"
    if json_body:
        body = json.loads(json_body)
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-digit-patterns")
def list_digit_patterns(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Digit Patterns for a Virtual Profile."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns"
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
    items = result.get("digitPatterns", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-digit-patterns")
def create_digit_patterns(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    name: str = typer.Option(None, "--name", help=""),
    pattern: str = typer.Option(None, "--pattern", help=""),
    action: str = typer.Option(None, "--action", help="e.g. BLOCK"),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Digit Pattern for a Virtual Profile."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns"
    if json_body:
        body = json.loads(json_body)
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



@app.command("update-digit-patterns-outgoing-permission")
def update_digit_patterns_outgoing_permission(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    use_custom_digit_patterns: bool = typer.Option(None, "--use-custom-digit-patterns/--no-use-custom-digit-patterns", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify the Digit Pattern Category Control Settings for a Virtual Profile."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if use_custom_digit_patterns is not None:
            body["useCustomDigitPatterns"] = use_custom_digit_patterns
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



@app.command("delete-digit-patterns-outgoing-permission")
def delete_digit_patterns_outgoing_permission(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete all Digit Patterns for a Virtual Profile."""
    if not force:
        typer.confirm(f"Delete {virtual_line_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {virtual_line_id}")



@app.command("show-digit-patterns")
def show_digit_patterns(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    digit_pattern_id: str = typer.Argument(help="digitPatternId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Specified Digit Pattern Details for a Virtual Profile."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
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



@app.command("update-digit-patterns-outgoing-permission-1")
def update_digit_patterns_outgoing_permission_1(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    digit_pattern_id: str = typer.Argument(help="digitPatternId"),
    name: str = typer.Option(None, "--name", help=""),
    pattern: str = typer.Option(None, "--pattern", help=""),
    action: str = typer.Option(None, "--action", help="e.g. TRANSFER_NUMBER_3"),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Digit Pattern for a Virtual Profile."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
    if json_body:
        body = json.loads(json_body)
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-digit-patterns-outgoing-permission-1")
def delete_digit_patterns_outgoing_permission_1(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    digit_pattern_id: str = typer.Argument(help="digitPatternId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Digit Pattern for a Virtual Profile."""
    if not force:
        typer.confirm(f"Delete {digit_pattern_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/outgoingPermission/digitPatterns/{digit_pattern_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {digit_pattern_id}")



@app.command("show-intercept")
def show_intercept(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Intercept Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/intercept"
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



@app.command("update-intercept")
def update_intercept(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Intercept Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/intercept"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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



@app.command("configure-call-intercept")
def configure_call_intercept(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Intercept Greeting for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/intercept/actions/announcementUpload/invoke"
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



@app.command("list-available-caller-ids")
def list_available_caller_ids(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Agent's List of Available Caller IDs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/agent/availableCallerIds"
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
    items = result.get("availableCallerIds", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-caller-id")
def list_caller_id(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Agent's Caller ID Information."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/agent/callerId"
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
    items = result.get("callerId", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-caller-id-agent")
def update_caller_id_agent(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    selected_caller_id: str = typer.Option(None, "--selected-caller-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Agent's Caller ID Information."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/agent/callerId"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected_caller_id is not None:
            body["selectedCallerId"] = selected_caller_id
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



@app.command("show-voicemail")
def show_voicemail(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Voicemail Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail"
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



@app.command("update-voicemail")
def update_voicemail(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Voicemail Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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



@app.command("configure-busy-voicemail")
def configure_busy_voicemail(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Busy Voicemail Greeting for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail/actions/uploadBusyGreeting/invoke"
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



@app.command("configure-no-answer")
def configure_no_answer(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure No Answer Voicemail Greeting for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail/actions/uploadNoAnswerGreeting/invoke"
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



@app.command("reset-voicemail-pin")
def reset_voicemail_pin(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reset Voicemail PIN for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail/actions/resetPin/invoke"
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



@app.command("update-passcode")
def update_passcode(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    passcode: str = typer.Option(None, "--passcode", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a virtual line's voicemail passcode."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/voicemail/passcode"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if passcode is not None:
            body["passcode"] = passcode
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



@app.command("show-music-on-hold")
def show_music_on_hold(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Music On Hold Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/musicOnHold"
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



@app.command("update-music-on-hold")
def update_music_on_hold(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    moh_enabled: bool = typer.Option(None, "--moh-enabled/--no-moh-enabled", help=""),
    greeting: str = typer.Option(None, "--greeting", help="e.g. CUSTOM"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Music On Hold Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/musicOnHold"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if moh_enabled is not None:
            body["mohEnabled"] = moh_enabled
        if greeting is not None:
            body["greeting"] = greeting
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



@app.command("show-push-to-talk")
def show_push_to_talk(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Push-to-Talk Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/pushToTalk"
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



@app.command("update-push-to-talk")
def update_push_to_talk(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    allow_auto_answer: bool = typer.Option(None, "--allow-auto-answer/--no-allow-auto-answer", help=""),
    connection_type: str = typer.Option(None, "--connection-type", help="e.g. TWO_WAY"),
    access_type: str = typer.Option(None, "--access-type", help="e.g. ALLOW_MEMBERS"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Push-to-Talk Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/pushToTalk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if allow_auto_answer is not None:
            body["allowAutoAnswer"] = allow_auto_answer
        if connection_type is not None:
            body["connectionType"] = connection_type
        if access_type is not None:
            body["accessType"] = access_type
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



@app.command("show-call-bridge")
def show_call_bridge(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Call Bridge Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callBridge"
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



@app.command("update-call-bridge")
def update_call_bridge(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    warning_tone_enabled: bool = typer.Option(None, "--warning-tone-enabled/--no-warning-tone-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Call Bridge Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callBridge"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if warning_tone_enabled is not None:
            body["warningToneEnabled"] = warning_tone_enabled
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



@app.command("show-barge-in")
def show_barge_in(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Barge In Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/bargeIn"
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



@app.command("update-barge-in")
def update_barge_in(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    tone_enabled: bool = typer.Option(None, "--tone-enabled/--no-tone-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Barge In Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/bargeIn"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if tone_enabled is not None:
            body["toneEnabled"] = tone_enabled
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



@app.command("show-privacy")
def show_privacy(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Virtual Line's Privacy Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/privacy"
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



@app.command("update-privacy")
def update_privacy(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    aa_extension_dialing_enabled: bool = typer.Option(None, "--aa-extension-dialing-enabled/--no-aa-extension-dialing-enabled", help=""),
    aa_naming_dialing_enabled: bool = typer.Option(None, "--aa-naming-dialing-enabled/--no-aa-naming-dialing-enabled", help=""),
    enable_phone_status_directory_privacy: bool = typer.Option(None, "--enable-phone-status-directory-privacy/--no-enable-phone-status-directory-privacy", help=""),
    enable_phone_status_pickup_barge_in_privacy: bool = typer.Option(None, "--enable-phone-status-pickup-barge-in-privacy/--no-enable-phone-status-pickup-barge-in-privacy", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure a Virtual Line's Privacy Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/privacy"
    if json_body:
        body = json.loads(json_body)
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-available-numbers-fax-message")
def list_available_numbers_fax_message(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual Line Fax Message Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/faxMessage/availableNumbers"
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
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-call-forwarding")
def list_available_numbers_call_forwarding(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `exten"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual Line Call Forward Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callForwarding/availableNumbers"
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
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-virtual-lines")
def list_available_numbers_virtual_lines(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of phone numbers for this location within th"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual Line Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/availableNumbers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
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
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-emergency-callback-number")
def list_available_numbers_emergency_callback_number(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual Line ECBN Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if owner_name is not None:
        params["ownerName"] = owner_name
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
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-call-intercept")
def list_available_numbers_call_intercept(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `exten"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual Line Call Intercept Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/callIntercept/availableNumbers"
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
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-do-not-disturb")
def show_do_not_disturb(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve DoNotDisturb Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/doNotDisturb"
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



@app.command("update-do-not-disturb")
def update_do_not_disturb(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    ring_splash_enabled: bool = typer.Option(None, "--ring-splash-enabled/--no-ring-splash-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify DoNotDisturb Settings for a Virtual Line."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/doNotDisturb"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if ring_splash_enabled is not None:
            body["ringSplashEnabled"] = ring_splash_enabled
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


