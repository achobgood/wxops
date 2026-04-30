import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling auto-attendant.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of auto attendants for this location."),
    name: str = typer.Option(None, "--name", help="Only return auto attendants with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return auto attendants with the matching phone number."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Auto Attendants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/autoAttendants"
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
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("autoAttendants", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="autoAttendants"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Enabled', 'enabled')], limit=limit)



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for an Auto Attendant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}"
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



@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    name: str = typer.Option(None, "--name", help="Unique name for the auto attendant."),
    phone_number: str = typer.Option(None, "--phone-number", help="Auto attendant phone number.  Either `phoneNumber` or `exten"),
    extension: str = typer.Option(None, "--extension", help="Auto attendant extension.  Either `phoneNumber` or `extensio"),
    first_name: str = typer.Option(None, "--first-name", help="First name defined for an auto attendant. This field has bee"),
    last_name: str = typer.Option(None, "--last-name", help="Last name defined for an auto attendant. This field has been"),
    language_code: str = typer.Option(None, "--language-code", help="Announcement language code for the auto attendant."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Business hours defined for the auto attendant."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Holiday defined for the auto attendant."),
    extension_dialing: str = typer.Option(None, "--extension-dialing", help="Choices: ENTERPRISE, GROUP"),
    name_dialing: str = typer.Option(None, "--name-dialing", help="Choices: ENTERPRISE, GROUP"),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone defined for the auto attendant."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name function"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Auto Attendant\n\nExample --json-body:\n  '{"name":"...","phoneNumber":"...","extension":"...","firstName":"...","lastName":"...","alternateNumbers":[{"phoneNumber":"...","ringPattern":"...","tollFreeNumber":"..."}],"languageCode":"...","businessSchedule":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}"
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
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if language_code is not None:
            body["languageCode"] = language_code
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
        if extension_dialing is not None:
            body["extensionDialing"] = extension_dialing
        if name_dialing is not None:
            body["nameDialing"] = name_dialing
        if time_zone is not None:
            body["timeZone"] = time_zone
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
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an Auto Attendant."""
    if not force:
        typer.confirm(f"Delete {auto_attendant_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {auto_attendant_id}")



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the auto attendant."),
    phone_number: str = typer.Option(None, "--phone-number", help="Auto attendant phone number.  Either `phoneNumber` or `exten"),
    extension: str = typer.Option(None, "--extension", help="Auto attendant extension.  Either `phoneNumber` or `extensio"),
    first_name: str = typer.Option(None, "--first-name", help="First name defined for an auto attendant. This field has bee"),
    last_name: str = typer.Option(None, "--last-name", help="Last name defined for an auto attendant. This field has been"),
    language_code: str = typer.Option(None, "--language-code", help="Announcement language code for the auto attendant."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="(required) Business hours defined for the auto attendant."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Holiday defined for the auto attendant."),
    extension_dialing: str = typer.Option(None, "--extension-dialing", help="Choices: ENTERPRISE, GROUP"),
    name_dialing: str = typer.Option(None, "--name-dialing", help="Choices: ENTERPRISE, GROUP"),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone defined for the auto attendant."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="The name to be used for dial by name functions.  Characters"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Auto Attendant\n\nExample --json-body:\n  '{"name":"...","businessSchedule":"...","businessHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"...","action":"...","description":"...","value":"...","audioAnnouncementFile":"..."},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"...","level":"..."},"callTreatment":{"retryAttemptForNoInput":"...","noInputTimer":"...","actionToBePerformed":"..."}},"afterHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"...","action":"...","description":"...","value":"...","audioAnnouncementFile":"..."},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"...","level":"..."},"callTreatment":{"retryAttemptForNoInput":"...","noInputTimer":"...","actionToBePerformed":"..."}},"phoneNumber":"...","extension":"...","firstName":"...","lastName":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants"
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
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if language_code is not None:
            body["languageCode"] = language_code
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
        if extension_dialing is not None:
            body["extensionDialing"] = extension_dialing
        if name_dialing is not None:
            body["nameDialing"] = name_dialing
        if time_zone is not None:
            body["timeZone"] = time_zone
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        _missing = [f for f in ['name', 'businessSchedule'] if f not in body or body[f] is None]
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



@app.command("show-call-forwarding")
def show_call_forwarding(
    location_id: str = typer.Argument(help="locationId"),
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Forwarding Settings for an Auto Attendant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding"
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
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Forwarding Settings for an Auto Attendant\n\nExample --json-body:\n  '{"callForwarding":{"always":{"enabled":"...","destination":"...","ringReminderEnabled":"...","sendToVoicemailEnabled":"..."},"selective":{"enabled":"...","destination":"...","ringReminderEnabled":"...","sendToVoicemailEnabled":"..."},"rules":["..."],"modes":["..."]}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding"
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
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the selective rule in the auto attendant."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines wh"),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines whe"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Selective Call Forwarding Rule for an Auto Attendant\n\nExample --json-body:\n  '{"name":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":"...","unavailableNumberEnabled":"...","numbers":"..."}},"enabled":true,"businessSchedule":"...","holidaySchedule":"...","callsTo":{"numbers":["..."]}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/selectiveRules"
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
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
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
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    rule_id: str = typer.Argument(help="ruleId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Forwarding Rule for an Auto Attendant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/selectiveRules/{rule_id}"
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
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    rule_id: str = typer.Argument(help="ruleId"),
    name: str = typer.Option(None, "--name", help="Unique name for the selective rule in the auto attendant."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines wh"),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines whe"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Selective Call Forwarding Rule for an Auto Attendant\n\nExample --json-body:\n  '{"name":"...","enabled":true,"businessSchedule":"...","holidaySchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":"...","unavailableNumberEnabled":"...","numbers":"..."}},"callsTo":{"numbers":["..."]}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/selectiveRules/{rule_id}"
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
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-selective-rules")
def delete_selective_rules(
    location_id: str = typer.Argument(help="locationId"),
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    rule_id: str = typer.Argument(help="ruleId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Forwarding Rule for an Auto Attendant."""
    if not force:
        typer.confirm(f"Delete {rule_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/selectiveRules/{rule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {rule_id}")



@app.command("list-available-numbers-auto-attendants")
def list_available_numbers_auto_attendants(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Auto Attendant Primary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/availableNumbers"
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Enabled', 'enabled')], limit=limit)



@app.command("list-available-numbers-alternate")
def list_available_numbers_alternate(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Auto Attendant Alternate Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/alternate/availableNumbers"
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Enabled', 'enabled')], limit=limit)



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
    """Get Auto Attendant Call Forward Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/callForwarding/availableNumbers"
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Enabled', 'enabled')], limit=limit)



@app.command("switch-mode-for")
def switch_mode_for(
    location_id: str = typer.Argument(help="locationId"),
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Call Forwarding Settings for an Auto Attendant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/actions/switchMode/invoke"
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



@app.command("delete-announcements")
def delete_announcements(
    location_id: str = typer.Argument(help="locationId"),
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    file_name: str = typer.Argument(help="fileName"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Auto Attendant Announcement File."""
    if not force:
        typer.confirm(f"Delete {file_name}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/announcements/{file_name}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {file_name}")



@app.command("list-announcements")
def list_announcements(
    location_id: str = typer.Argument(help="locationId"),
    auto_attendant_id: str = typer.Argument(help="autoAttendantId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Auto Attendant Announcement Files."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/announcements"
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Enabled', 'enabled')], limit=limit)


