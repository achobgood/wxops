import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling hunt-group.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Only return hunt groups with matching location ID."),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    name: str = typer.Option(None, "--name", help="Only return hunt groups with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return hunt groups with the matching primary phone numb"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Hunt Groups."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/huntGroups"
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
    items = result.get("huntGroups", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    language_code: str = typer.Option(None, "--language-code", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    time_zone: str = typer.Option(None, "--time-zone", help=""),
    hunt_group_caller_id_for_outgoing_calls_enabled: bool = typer.Option(None, "--hunt-group-caller-id-for-outgoing-calls-enabled/--no-hunt-group-caller-id-for-outgoing-calls-enabled", help=""),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if enabled is not None:
            body["enabled"] = enabled
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
        if hunt_group_caller_id_for_outgoing_calls_enabled is not None:
            body["huntGroupCallerIdForOutgoingCallsEnabled"] = hunt_group_caller_id_for_outgoing_calls_enabled
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
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Hunt Group."""
    if not force:
        typer.confirm(f"Delete {hunt_group_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {hunt_group_id}")



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}"
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
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    name: str = typer.Option(None, "--name", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    distinctive_ring: bool = typer.Option(None, "--distinctive-ring/--no-distinctive-ring", help=""),
    language_code: str = typer.Option(None, "--language-code", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    time_zone: str = typer.Option(None, "--time-zone", help=""),
    hunt_group_caller_id_for_outgoing_calls_enabled: bool = typer.Option(None, "--hunt-group-caller-id-for-outgoing-calls-enabled/--no-hunt-group-caller-id-for-outgoing-calls-enabled", help=""),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}"
    if json_body:
        body = json.loads(json_body)
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
    location_id: str = typer.Argument(help="locationId"),
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Forwarding Settings for a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding"
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
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Forwarding Settings for a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding"
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
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    name: str = typer.Option(None, "--name", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help=""),
    business_schedule: str = typer.Option(None, "--business-schedule", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Selective Call Forwarding Rule for a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/selectiveRules"
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
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    rule_id: str = typer.Argument(help="ruleId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Forwarding Rule for a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/selectiveRules/{rule_id}"
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
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    rule_id: str = typer.Argument(help="ruleId"),
    name: str = typer.Option(None, "--name", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help=""),
    business_schedule: str = typer.Option(None, "--business-schedule", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Selective Call Forwarding Rule for a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/selectiveRules/{rule_id}"
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
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    rule_id: str = typer.Argument(help="ruleId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Forwarding Rule for a Hunt Group."""
    if not force:
        typer.confirm(f"Delete {rule_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/selectiveRules/{rule_id}"
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



@app.command("list-available-numbers-hunt-groups")
def list_available_numbers_hunt_groups(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hunt Group Primary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/availableNumbers"
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



@app.command("list-available-numbers-alternate")
def list_available_numbers_alternate(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Hunt Group Alternate Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/alternate/availableNumbers"
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



@app.command("list-available-numbers-call-forwarding")
def list_available_numbers_call_forwarding(
    location_id: str = typer.Argument(help="locationId"),
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
    """Get Hunt Group Call Forward Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/callForwarding/availableNumbers"
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



@app.command("switch-mode-for")
def switch_mode_for(
    location_id: str = typer.Argument(help="locationId"),
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Call Forwarding Settings for a Hunt Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/huntGroups/{hunt_group_id}/callForwarding/actions/switchMode/invoke"
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


