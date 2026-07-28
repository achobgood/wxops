import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling numbers.")


_BODY_SKELETON_CREATE = '{"phoneNumbers":["..."],"numberType":"TOLLFREE","numberUsageType":"NONE","state":"ACTIVE","subscriptionId":"...","carrierId":"..."}'

@app.command("create", short_help="Add Phone Numbers to a Location.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    number_type: str = typer.Option(None, "--number-type", help="Choices: TOLLFREE, DID, MOBILE"),
    number_usage_type: str = typer.Option(None, "--number-usage-type", help="Choices: NONE, SERVICE"),
    state: str = typer.Option(None, "--state", help="Choices: ACTIVE, INACTIVE"),
    subscription_id: str = typer.Option(None, "--subscription-id", help="The `subscriptionId` to be used for the mobile number order."),
    carrier_id: str = typer.Option(None, "--carrier-id", help="The `carrierId` to be used for the mobile number order."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add Phone Numbers to a Location.\n\n\b\nExample: wxcli numbers create LOCATION_ID\n\n\b\nExample --json-body: '{"phoneNumbers":["..."],"numberType":"TOLLFREE","numberUsageType":"NONE","state":"ACTIVE","subscriptionId":"...","carrierId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/numbers"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if number_type is not None:
            body["numberType"] = number_type
        if number_usage_type is not None:
            body["numberUsageType"] = number_usage_type
        if state is not None:
            body["state"] = state
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if carrier_id is not None:
            body["carrierId"] = carrier_id
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



_BODY_SKELETON_UPDATE = '{"phoneNumbers":["..."],"action":"ACTIVATE"}'

@app.command("update", short_help="Manage Number State in a Location.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    action: str = typer.Option(None, "--action", help="Choices: ACTIVATE, DEACTIVATE"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Manage Number State in a Location.\n\n\b\nExample: wxcli numbers update LOCATION_ID\n\n\b\nExample --json-body: '{"phoneNumbers":["..."],"action":"ACTIVATE"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/numbers"
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



_BODY_SKELETON_DELETE = '{"phoneNumbers":["..."]}'

@app.command("delete", short_help="Remove Phone Numbers from a Location.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove Phone Numbers from a Location.\n\n\b\nExample: wxcli numbers delete LOCATION_ID\n\n\b\nExample --json-body: '{"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Numbers for {location_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/numbers"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    missing = [f for f in ['phoneNumbers'] if f not in body]
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
        typer.echo(f"Deleted: {location_id}")
    else:
        emit({"status": "removed", "id": location_id}, output=output, fields=fields)



_BODY_SKELETON_VALIDATE_PHONE_NUMBERS = '{"phoneNumbers":["..."]}'

@app.command("validate-phone-numbers", short_help="Validate Phone Numbers.")
def validate_phone_numbers(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate Phone Numbers.\n\n\b\nExample --json-body: '{"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_PHONE_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/actions/validateNumbers/invoke"
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



@app.command("list", short_help="Get Phone Numbers for an Organization with Given Criteria.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of phone numbers for this location within the given organization. The maximum length is 36."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search for this `phoneNumber`."),
    available: str = typer.Option(None, "--available", help="Search among the available phone numbers. This parameter cannot be used along with `ownerType` parameter when set to `true`."),
    order: str = typer.Option(None, "--order", help="Sort the list of phone numbers based on the following:`lastName`,`dn`,`extension`. Sorted by number and extension in ascending order."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    owner_id: str = typer.Option(None, "--owner-id", help="Returns only the matched number/extension entries assigned to the feature with the specified UUID or `broadsoftId`."),
    owner_type: str = typer.Option(None, "--owner-type", help="Choices: PEOPLE, PLACE, AUTO_ATTENDANT, CALL_QUEUE, PAGING_GROUP, HUNT_GROUP, VOICE_MESSAGING, BROADWORKS_ANYWHERE, CONTACT_CENTER_LINK, ROUTE_LIST, VOICEMAIL_GROUP, VIRTUAL_LINE"),
    extension: str = typer.Option(None, "--extension", help="Returns the list of phone numbers with the given extension."),
    number_type: str = typer.Option(None, "--number-type", help="Choices: NUMBER, EXTENSION"),
    phone_number_type: str = typer.Option(None, "--phone-number-type", help="Choices: PRIMARY, ALTERNATE, FAX, DNIS, Default"),
    state: str = typer.Option(None, "--state", help="Choices: ACTIVE, INACTIVE, Default"),
    details: str = typer.Option(None, "--details", help="Returns the overall count of the phone numbers along with other details for a given organization."),
    toll_free_numbers: str = typer.Option(None, "--toll-free-numbers", help="Returns the list of toll-free phone numbers."),
    restricted_non_geo_numbers: str = typer.Option(None, "--restricted-non-geo-numbers", help="Returns the list of restricted non-geographical numbers."),
    included_telephony_types: str = typer.Option(None, "--included-telephony-types", help="Returns the list of phone numbers that are of given `includedTelephonyTypes`. By default, if this query parameter is not provided, it will list both PSTN and Mobile Numbers. Possible input values are PSTN_NUMBER or MOBILE_NUMBER."),
    service_number: str = typer.Option(None, "--service-number", help="Returns the list of service phone numbers."),
    reserved_number: str = typer.Option(None, "--reserved-number", help="Filters reserved phone numbers. When set to `true`, returns only reserved phone numbers. When set to `false`, returns only non-reserved phone numbers. When omitted, no reserved-number filter is applied. Reserved numbers cannot be assigned to people, features, or services. This parameter cannot be..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Phone Numbers for an Organization with Given Criteria."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/numbers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if available is not None:
        params["available"] = available
    if order is not None:
        params["order"] = order
    if owner_name is not None:
        params["ownerName"] = owner_name
    if owner_id is not None:
        params["ownerId"] = owner_id
    if owner_type is not None:
        params["ownerType"] = owner_type
    if extension is not None:
        params["extension"] = extension
    if number_type is not None:
        params["numberType"] = number_type
    if phone_number_type is not None:
        params["phoneNumberType"] = phone_number_type
    if state is not None:
        params["state"] = state
    if details is not None:
        params["details"] = details
    if toll_free_numbers is not None:
        params["tollFreeNumbers"] = toll_free_numbers
    if restricted_non_geo_numbers is not None:
        params["restrictedNonGeoNumbers"] = restricted_non_geo_numbers
    if included_telephony_types is not None:
        params["includedTelephonyTypes"] = included_telephony_types
    if service_number is not None:
        params["serviceNumber"] = service_number
    if reserved_number is not None:
        params["reservedNumber"] = reserved_number
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('State', 'state'), ('Owner Type', 'owner.type'), ('Owner Name', 'owner.firstName')], limit=limit)



@app.command("list-manage-numbers", short_help="List Manage Numbers Jobs.")
def list_manage_numbers(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Manage Numbers Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/numbers/manageNumbers"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Tracking ID', 'trackingId'), ('Status', 'latestExecutionStatus')], limit=limit)



_BODY_SKELETON_CREATE_MANAGE_NUMBERS = '{"operation":"...","numberList":[{"locationId":"...","numbers":"..."}],"targetLocationId":"...","numberUsageType":"..."}'

@app.command("create-manage-numbers", short_help="Initiate Number Jobs.")
def create_manage_numbers(
    operation: str = typer.Option(None, "--operation", help="(required) The kind of operation to be carried out."),
    target_location_id: str = typer.Option(None, "--target-location-id", help="Mandatory for a `MOVE` operation. The target location within organization where the unassigned numbers will be moved from the source location."),
    number_usage_type: str = typer.Option(None, "--number-usage-type", help="The number usage type. Mandatory for `NUMBER_USAGE_CHANGE` operation."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Initiate Number Jobs.\n\n\b\nExample: wxcli numbers create-manage-numbers --operation OPERATION\n\n\b\nExample --json-body: '{"operation":"...","numberList":[{"locationId":"...","numbers":"..."}],"targetLocationId":"...","numberUsageType":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_MANAGE_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/numbers/manageNumbers"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if operation is not None:
            body["operation"] = operation
        if target_location_id is not None:
            body["targetLocationId"] = target_location_id
        if number_usage_type is not None:
            body["numberUsageType"] = number_usage_type
        _missing = [f for f in ['operation'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Manage Numbers Job Status.")
def show(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli numbers list-manage-numbers"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Manage Numbers Job Status.\n\n\b\nExample: wxcli numbers show JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/numbers/manageNumbers/{job_id}"
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



@app.command("pause-the-manage", short_help="Pause the Manage Numbers Job.")
def pause_the_manage(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli numbers list-manage-numbers"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause the Manage Numbers Job.\n\n\b\nExample: wxcli numbers pause-the-manage JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/numbers/manageNumbers/{job_id}/actions/pause/invoke"
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



@app.command("resume-the-manage", short_help="Resume the Manage Numbers Job.")
def resume_the_manage(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli numbers list-manage-numbers"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume the Manage Numbers Job.\n\n\b\nExample: wxcli numbers resume-the-manage JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/numbers/manageNumbers/{job_id}/actions/resume/invoke"
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



@app.command("list-errors", short_help="List Manage Numbers Job Errors.")
def list_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli numbers list-manage-numbers"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Manage Numbers Job Errors.\n\n\b\nExample: wxcli numbers list-errors JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/numbers/manageNumbers/{job_id}/errors"
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


