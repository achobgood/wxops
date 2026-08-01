import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling pstn.")


@app.command("list", short_help="Retrieve PSTN Connection Options for a Location.")
def cmd_list(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    service_types: str = typer.Option(None, "--service-types", help="Use the `serviceTypes` parameter to fetch connections for the following services * `MOBILE_NUMBERS`"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve PSTN Connection Options for a Location.\n\n\b\nExample: wxcli pstn list LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/connectionOptions"
    params = {}
    if service_types is not None:
        params["serviceTypes"] = service_types
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'displayName'), ('PSTN Services', 'pstnServices')], limit=limit)



@app.command("list-connection", short_help="Retrieve PSTN Connection for a Location.")
def list_connection(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve PSTN Connection for a Location.\n\n\b\nExample: wxcli pstn list-connection LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/connection"
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



_BODY_SKELETON_UPDATE = '{"id":"...","premiseRouteType":"...","premiseRouteId":"..."}'

@app.command("update", short_help="Setup PSTN Connection for a Location.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    id_param: str = typer.Option(None, "--id", help="A unique identifier for the connection. This is required for non-integrated CCP."),
    premise_route_type: str = typer.Option(None, "--premise-route-type", help="Premise route type. The possible types are TRUNK and ROUTE_GROUP. This is required for the local gateway."),
    premise_route_id: str = typer.Option(None, "--premise-route-id", help="Premise route ID. This refers to either a Trunk ID or a Route Group ID and is required for the local gateway."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Setup PSTN Connection for a Location.\n\n\b\nExample: wxcli pstn update LOCATION_ID\n\n\b\nExample --json-body: '{"id":"...","premiseRouteType":"...","premiseRouteId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/connection"
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
        if premise_route_type is not None:
            body["premiseRouteType"] = premise_route_type
        if premise_route_id is not None:
            body["premiseRouteId"] = premise_route_id
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_EMERGENCY_ADDRESS = '{"emergencyAddress":{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}}'

@app.command("update-emergency-address", short_help="Update the Emergency Address for a Phone Number.")
def update_emergency_address(
    phone_number: str = typer.Argument(help="Webex PHONE_NUMBER id"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Emergency Address for a Phone Number.\n\n\b\nExample: wxcli pstn update-emergency-address PHONE_NUMBER\n\n\b\nExample --json-body: '{"emergencyAddress":{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EMERGENCY_ADDRESS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/numbers/{phone_number}/emergencyAddress"
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
        emit({"status": "updated", "id": phone_number}, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}'

@app.command("create", short_help="Emergency Address Lookup to Verify if Address is Valid.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    address1: str = typer.Option(None, "--address1", help="Primary street information for the emergency address."),
    address2: str = typer.Option(None, "--address2", help="Apartment number or any other secondary information for the emergency address."),
    city: str = typer.Option(None, "--city", help="City for the emergency address."),
    state: str = typer.Option(None, "--state", help="State or Province or Region for the emergency address."),
    postal_code: str = typer.Option(None, "--postal-code", help="Postal code for the emergency address."),
    country: str = typer.Option(None, "--country", help="Country for the emergency address."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Emergency Address Lookup to Verify if Address is Valid.\n\n\b\nExample: wxcli pstn create LOCATION_ID\n\n\b\nExample --json-body: '{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/emergencyAddress/lookup"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if address1 is not None:
            body["address1"] = address1
        if address2 is not None:
            body["address2"] = address2
        if city is not None:
            body["city"] = city
        if state is not None:
            body["state"] = state
        if postal_code is not None:
            body["postalCode"] = postal_code
        if country is not None:
            body["country"] = country
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



_BODY_SKELETON_CREATE_EMERGENCY_ADDRESS = '{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}'

@app.command("create-emergency-address", short_help="Add an Emergency Address to a Location.")
def create_emergency_address(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    address1: str = typer.Option(None, "--address1", help="Primary street information for the emergency address."),
    address2: str = typer.Option(None, "--address2", help="Apartment number or any other secondary information for the emergency address."),
    city: str = typer.Option(None, "--city", help="City for the emergency address."),
    state: str = typer.Option(None, "--state", help="State or Province or Region for the emergency address."),
    postal_code: str = typer.Option(None, "--postal-code", help="Postal code for the emergency address."),
    country: str = typer.Option(None, "--country", help="Country for the emergency address."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add an Emergency Address to a Location.\n\n\b\nExample: wxcli pstn create-emergency-address LOCATION_ID\n\n\b\nExample --json-body: '{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_EMERGENCY_ADDRESS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/emergencyAddress"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if address1 is not None:
            body["address1"] = address1
        if address2 is not None:
            body["address2"] = address2
        if city is not None:
            body["city"] = city
        if state is not None:
            body["state"] = state
        if postal_code is not None:
            body["postalCode"] = postal_code
        if country is not None:
            body["country"] = country
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



_BODY_SKELETON_UPDATE_EMERGENCY_ADDRESSES = '{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}'

@app.command("update-emergency-addresses", short_help="Update the Emergency Address of a Location.")
def update_emergency_addresses(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    address_id: str = typer.Argument(help="Webex EMERGENCY_ADDRESS id"),
    address1: str = typer.Option(None, "--address1", help="Primary street information for the emergency address."),
    address2: str = typer.Option(None, "--address2", help="Apartment number or any other secondary information for the emergency address."),
    city: str = typer.Option(None, "--city", help="City for the emergency address."),
    state: str = typer.Option(None, "--state", help="State or Province or Region for the emergency address."),
    postal_code: str = typer.Option(None, "--postal-code", help="Postal code for the emergency address."),
    country: str = typer.Option(None, "--country", help="Country for the emergency address."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Emergency Address of a Location.\n\n\b\nExample: wxcli pstn update-emergency-addresses LOCATION_ID ADDRESS_ID\n\n\b\nExample --json-body: '{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EMERGENCY_ADDRESSES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/emergencyAddresses/{address_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if address1 is not None:
            body["address1"] = address1
        if address2 is not None:
            body["address2"] = address2
        if city is not None:
            body["city"] = city
        if state is not None:
            body["state"] = state
        if postal_code is not None:
            body["postalCode"] = postal_code
        if country is not None:
            body["country"] = country
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
        emit({"status": "updated", "id": address_id}, output=output, fields=fields)


