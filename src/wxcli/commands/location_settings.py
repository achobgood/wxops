import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling location-settings.")


@app.command("list")
def cmd_list(
    dial_plan_id: str = typer.Argument(help="dialPlanId"),
    dial_pattern: str = typer.Option(None, "--dial-pattern", help="An enterprise dial pattern is represented by a sequence of d"),
    order: str = typer.Option(None, "--order", help="Order the dial patterns according to the designated fields."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Dial Patterns."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("dialPatterns", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-1")
def list_1(
    name: str = typer.Option(None, "--name", help="List locations whose name contains this string."),
    order: str = typer.Option(None, "--order", help="Sort the list of locations based on `name`, either asc or de"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
            items = result.get("locations", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="locations"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    id_param: str = typer.Option(None, "--id", help="(required) A unique identifier for the location."),
    name: str = typer.Option(None, "--name", help="(required) The name of the location."),
    time_zone: str = typer.Option(None, "--time-zone", help="(required) Time zone associated with this location. Refer to this link"),
    preferred_language: str = typer.Option(None, "--preferred-language", help="(required) Default email language."),
    announcement_language: str = typer.Option(None, "--announcement-language", help="(required) Location's phone announcement language."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Enable a Location for Webex Calling\n\nExample --json-body:\n  '{"id":"...","name":"...","timeZone":"...","preferredLanguage":"...","announcementLanguage":"...","address":{"address1":"...","city":"...","state":"...","postalCode":"...","country":"...","address2":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Webex Calling Details."""
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
    announcement_language: str = typer.Option(None, "--announcement-language", help="Location's phone announcement language."),
    external_caller_id_name: str = typer.Option(None, "--external-caller-id-name", help="External caller ID name value. Unicode characters."),
    p_access_network_info: str = typer.Option(None, "--p-access-network-info", help="Emergency Location Identifier for a location. The `pAccessNe"),
    outside_dial_digit: str = typer.Option(None, "--outside-dial-digit", help="Must dial to reach an outside line. Default is none."),
    enforce_outside_dial_digit: bool = typer.Option(None, "--enforce-outside-dial-digit/--no-enforce-outside-dial-digit", help="True when enforcing outside dial digit at location level to"),
    routing_prefix: str = typer.Option(None, "--routing-prefix", help="Must dial a prefix when calling between locations having sam"),
    charge_number: str = typer.Option(None, "--charge-number", help="Set the chargeable number for the line placing the call.  Wh"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Location Webex Calling Details\n\nExample --json-body:\n  '{"announcementLanguage":"...","callingLineId":{"name":"...","phoneNumber":"..."},"connection":{"type":"ROUTE_GROUP","id":"..."},"externalCallerIdName":"...","pAccessNetworkInfo":"...","outsideDialDigit":"...","enforceOutsideDialDigit":true,"routingPrefix":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("list-update-routing-prefix")
def list_update_routing_prefix(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Status', 'latestExecutionStatus')], limit=limit)



@app.command("show-update-routing-prefix")
def show_update_routing_prefix(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the job status of Update Routing Prefix job."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("show-errors")
def show_errors(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get job errors for update routing prefix job."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("change-announcement-language")
def change_announcement_language(
    location_id: str = typer.Argument(help="locationId"),
    agent_enabled: str = typer.Option(None, "--agent-enabled", help="Set to `true` to change announcement language for existing p"),
    service_enabled: str = typer.Option(None, "--service-enabled", help="Set to `true` to change announcement language for existing f"),
    announcement_language_code: str = typer.Option(None, "--announcement-language-code", help="Language code."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Change Announcement Language."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/actions/modifyAnnouncementLanguage/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    print_json(result)



@app.command("show-emergency-callback-number")
def show_emergency_callback_number(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location Emergency callback number."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-emergency-callback-number")
def update_emergency_callback_number(
    location_id: str = typer.Argument(help="locationId"),
    selected: str = typer.Option(None, "--selected", help="Choices: LOCATION_NUMBER, LOCATION_MEMBER_NUMBER"),
    location_member_id: str = typer.Option(None, "--location-member-id", help="Member ID of user/place/virtual line/hunt group within the l"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location Emergency callback number\n\nExample --json-body:\n  '{"selected":"LOCATION_NUMBER","locationMemberId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/features/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("validate-the-list")
def validate_the_list(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate the List of Extensions\n\nExample --json-body:\n  '{"extensions":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/actions/validateExtensions/invoke"
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



@app.command("validate-extensions")
def validate_extensions(
    location_id: str = typer.Argument(help="locationId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate Extensions\n\nExample --json-body:\n  '{"extensions":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/actions/validateExtensions/invoke"
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



@app.command("show-music-on-hold")
def show_music_on_hold(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Music On Hold."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-music-on-hold")
def update_music_on_hold(
    location_id: str = typer.Argument(help="locationId"),
    moh_enabled: bool = typer.Option(None, "--moh-enabled/--no-moh-enabled", help="Music on hold is enabled or disabled for the workspace."),
    greeting: str = typer.Option(None, "--greeting", help="Choices: DEFAULT, CUSTOM"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Music On Hold\n\nExample --json-body:\n  '{"mohEnabled":true,"greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/musicOnHold"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("show-private-network-connect")
def show_private_network_connect(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Private Network Connect."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-private-network-connect")
def update_private_network_connect(
    location_id: str = typer.Argument(help="locationId"),
    network_connection_type: str = typer.Option(None, "--network-connection-type", help="Choices: PUBLIC_INTERNET, PRIVATE_NETWORK"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Private Network Connect."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/privateNetworkConnect"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if network_connection_type is not None:
            body["networkConnectionType"] = network_connection_type
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-route-choices")
def list_route_choices(
    route_group_name: str = typer.Option(None, "--route-group-name", help="Return the list of route identities matching the Route group"),
    trunk_name: str = typer.Option(None, "--trunk-name", help="Return the list of route identities matching the Trunk name."),
    order: str = typer.Option(None, "--order", help="Order the route identities according to the designated field"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("routeIdentities", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers-external-caller-id")
def list_available_numbers_external_caller_id(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the provided list in the `phon"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    person_id: str = typer.Option(None, "--person-id", help="Retrieve available external caller ID numbers for this perso"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the List of Phone Numbers Available for External Caller ID."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-locations")
def list_available_numbers_locations(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Phone Numbers for a Location with Given Criteria."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-webex-go")
def list_available_numbers_webex_go(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Webex Go Available Phone Numbers."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-emergency-callback-number")
def list_available_numbers_emergency_callback_number(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location ECBN Available Phone Numbers."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-available-numbers-call-intercept")
def list_available_numbers_call_intercept(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    extension: str = typer.Option(None, "--extension", help="Returns the list of phone numbers with the given `extension`"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Call Intercept Available Phone Numbers."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-directories")
def list_directories(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read list of Receptionist Contact Directories."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("directories", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-directories")
def create_directories(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) Receptionist Contact Directory name. The directory name shou"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Receptionist Contact Directory\n\nExample --json-body:\n  '{"name":"...","contacts":[{"personId":"...","featureId":"...","type":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/receptionistContacts/directories"
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



@app.command("show-directories")
def show_directories(
    location_id: str = typer.Argument(help="locationId"),
    directory_id: str = typer.Argument(help="directoryId"),
    search_criteria_mode_or: str = typer.Option(None, "--search-criteria-mode-or", help="When `true`, results matching any one of the search criteria"),
    first_name: str = typer.Option(None, "--first-name", help="Search for directories that contain people with the indicate"),
    last_name: str = typer.Option(None, "--last-name", help="Search for directories that contain people with the indicate"),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for directories that contain people with the indicate"),
    extension: str = typer.Option(None, "--extension", help="Search for directories that contain people with the indicate"),
    person_id: str = typer.Option(None, "--person-id", help="Search for directories that contain people with the indicate"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get details for a Receptionist Contact Directory."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-directories")
def update_directories(
    location_id: str = typer.Argument(help="locationId"),
    directory_id: str = typer.Argument(help="directoryId"),
    name: str = typer.Option(None, "--name", help="Receptionist Contact Directory name. The directory name shou"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Receptionist Contact Directory\n\nExample --json-body:\n  '{"name":"...","contacts":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/receptionistContacts/directories/{directory_id}"
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
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    location_id: str = typer.Argument(help="locationId"),
    directory_id: str = typer.Argument(help="directoryId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Receptionist Contact Directory."""
    if not force:
        typer.confirm(f"Delete {directory_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/receptionistContacts/directories/{directory_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {directory_id}")



@app.command("list-available-numbers-charge-number")
def list_available_numbers_charge_number(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Charge Numbers for a Location with Given Criteria."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



@app.command("list-delete-calling-location")
def list_delete_calling_location(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Status', 'latestExecutionStatus')], limit=limit)



@app.command("create-delete-calling-location")
def create_delete_calling_location(
    location_id: str = typer.Option(None, "--location-id", help="(required) Unique identifier for the calling location to disable."),
    location_name: str = typer.Option(None, "--location-name", help="Name of the calling location to disable."),
    force_delete: bool = typer.Option(None, "--force-delete/--no-force-delete", help="Force delete is only applicable when calling features like c"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Disable a Location for Webex Calling."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("safe-delete-check")
def safe_delete_check(
    location_id: str = typer.Argument(help="locationId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Safe Delete Check Before Disabling a Location for Webex Calling."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/actions/precheckForDeletion/invoke"
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



@app.command("pause-a-disable")
def pause_a_disable(
    job_id: str = typer.Argument(help="jobId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause a Disable Calling Location Job."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation/{job_id}/actions/pause/invoke"
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



@app.command("resume-a-paused")
def resume_a_paused(
    job_id: str = typer.Argument(help="jobId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume a Paused Disable Calling Location Job."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/locations/deleteCallingLocation/{job_id}/actions/resume/invoke"
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



@app.command("list-errors")
def list_errors(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Errors for a Disable Calling Location Job."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-delete-calling-location")
def show_delete_calling_location(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Disable Calling Location Job Status."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("show-call-captions")
def show_call_captions(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the location call captions settings."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-call-captions")
def update_call_captions(
    location_id: str = typer.Argument(help="locationId"),
    location_closed_captions_enabled: bool = typer.Option(None, "--location-closed-captions-enabled/--no-location-closed-captions-enabled", help="Enable or disable location-level closed captions."),
    location_transcripts_enabled: bool = typer.Option(None, "--location-transcripts-enabled/--no-location-transcripts-enabled", help="Enable or disable location-level transcripts."),
    use_org_settings_enabled: bool = typer.Option(None, "--use-org-settings-enabled/--no-use-org-settings-enabled", help="If `useOrgSettingsEnabled` is `true`, organization-level set"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the location call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callCaptions"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")


