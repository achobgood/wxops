import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling dect-devices.")


_BODY_SKELETON_CREATE = '{"name":"...","model":"DMS Cisco DBS110","defaultAccessCodeEnabled":true,"defaultAccessCode":"...","displayName":"..."}'

@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) Name of the DECT network. Min and max length supported for the DECT network name are 1 and 40 respectively."),
    display_name: str = typer.Option(None, "--display-name", help="Add a default name (11 characters max) to display for all handsets. If left blank, the default name will be an indexed number followed by the DECT network name."),
    model: str = typer.Option(None, "--model", help="(required) Choices: DMS Cisco DBS110, Cisco DECT 110 Base, DMS Cisco DBS210, Cisco DECT 210 Base"),
    default_access_code_enabled: bool = typer.Option(None, "--default-access-code-enabled/--no-default-access-code-enabled", help="(required) If set to true, need to provide a default access code that will be shared for all users in this network to pair their lines to the next available handset. Otherwise, each user will get a unique 4-digit access code that will be auto-generated. Note: There is currently no public API to retrieve the..."),
    default_access_code: str = typer.Option(None, "--default-access-code", help="(required) If `defaultAccessCodeEnabled` is set to true, then provide a default access code that needs to be a 4-numeric digit. The access code should be unique to the DECT network for the location."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a DECT Network\n\nExample --json-body:\n  '{"name":"...","model":"DMS Cisco DBS110","defaultAccessCodeEnabled":true,"defaultAccessCode":"...","displayName":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks"
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
        if display_name is not None:
            body["displayName"] = display_name
        if model is not None:
            body["model"] = model
        if default_access_code_enabled is not None:
            body["defaultAccessCodeEnabled"] = default_access_code_enabled
        if default_access_code is not None:
            body["defaultAccessCode"] = default_access_code
        _missing = [f for f in ['name', 'model', 'defaultAccessCodeEnabled', 'defaultAccessCode'] if f not in body or body[f] is None]
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
        if isinstance(result, dict) and "dectNetworkId" in result:
            typer.echo(f"Created: {result['dectNetworkId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("list")
def cmd_list(
    name: str = typer.Option(None, "--name", help="List of DECT networks with this name."),
    location_id: str = typer.Option(None, "--location-id", help="List of DECT networks at this location."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the List of DECT Networks for an organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/dectNetworks"
    params = {}
    if name is not None:
        params["name"] = name
    if location_id is not None:
        params["locationId"] = location_id
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get DECT Network Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}"
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



_BODY_SKELETON_UPDATE = '{"name":"...","defaultAccessCodeEnabled":true,"defaultAccessCode":"...","displayName":"..."}'

@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    name: str = typer.Option(None, "--name", help="Name of the DECT network. This should be unique across the location."),
    display_name: str = typer.Option(None, "--display-name", help="DECT network name that will be displayed on the handset."),
    default_access_code_enabled: bool = typer.Option(None, "--default-access-code-enabled/--no-default-access-code-enabled", help="Default access code is enabled. If true, the default access code is mandatory. If false, an auto-generated access code is used."),
    default_access_code: str = typer.Option(None, "--default-access-code", help="Default access code for the DECT network. The default access code should be unique within the same location to avoid the handset accidentally registering with base stations from different DECT networks in range. This is mandatory when `defaultAccessCodeEnabled` is true."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update DECT Network\n\nExample --json-body:\n  '{"name":"...","defaultAccessCodeEnabled":true,"defaultAccessCode":"...","displayName":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}"
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
        if display_name is not None:
            body["displayName"] = display_name
        if default_access_code_enabled is not None:
            body["defaultAccessCodeEnabled"] = default_access_code_enabled
        if default_access_code is not None:
            body["defaultAccessCode"] = default_access_code
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("delete")
def delete(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete DECT Network."""
    if not force:
        typer.confirm(f"Delete {dect_network_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}"
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
    else:
        typer.echo(f"Deleted: {dect_network_id}")



@app.command("list-base-stations")
def list_base_stations(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a list of DECT Network Base Stations."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/baseStations"
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
    items = result.get("baseStations", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



_BODY_SKELETON_CREATE_BASE_STATIONS = '{"baseStationMacs":["..."]}'

@app.command("create-base-stations")
def create_base_stations(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Multiple Base Stations\n\nExample --json-body:\n  '{"baseStationMacs":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BASE_STATIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/baseStations"
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
        if isinstance(result, dict) and "baseStations" in result:
            typer.echo(f"Created: {result['baseStations']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("delete-base-stations-dect-networks")
def delete_base_stations_dect_networks(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete bulk DECT Network Base Stations."""
    if not force:
        typer.confirm(f"Delete {dect_network_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/baseStations"
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
    else:
        typer.echo(f"Deleted: {dect_network_id}")



@app.command("show-base-stations")
def show_base_stations(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    base_station_id: str = typer.Argument(help="baseStationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the details of a specific DECT Network Base Station."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/baseStations/{base_station_id}"
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



@app.command("delete-base-stations-dect-networks-1")
def delete_base_stations_dect_networks_1(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    base_station_id: str = typer.Argument(help="baseStationId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a specific DECT Network Base Station."""
    if not force:
        typer.confirm(f"Delete {base_station_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/baseStations/{base_station_id}"
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
    else:
        typer.echo(f"Deleted: {base_station_id}")



@app.command("list-handsets")
def list_handsets(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    basestation_id: str = typer.Option(None, "--basestation-id", help="Search handset details in the specified DECT base station ID."),
    member_id: str = typer.Option(None, "--member-id", help="ID of the member of the handset. Members can be of type PEOPLE, PLACE, or VIRTUAL_LINE."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of Handsets for a DECT Network ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets"
    params = {}
    if basestation_id is not None:
        params["basestationId"] = basestation_id
    if member_id is not None:
        params["memberId"] = member_id
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
    items = result.get("handsets", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



_BODY_SKELETON_CREATE_HANDSETS = '{"line1MemberId":"...","customDisplayName":"...","line2MemberId":"..."}'

@app.command("create-handsets")
def create_handsets(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    line1_member_id: str = typer.Option(None, "--line1-member-id", help="(required) ID of the member on line1 of the handset. Members can be PEOPLE or PLACE."),
    line2_member_id: str = typer.Option(None, "--line2-member-id", help="ID of the member on line2 of the handset. Members can be PEOPLE, PLACE, or VIRTUAL_LINE."),
    custom_display_name: str = typer.Option(None, "--custom-display-name", help="(required) Custom display name on the handset. Min and max length supported for the custom display name is 1 and 16 respectively."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a Handset to a DECT Network\n\nExample --json-body:\n  '{"line1MemberId":"...","customDisplayName":"...","line2MemberId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_HANDSETS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if line1_member_id is not None:
            body["line1MemberId"] = line1_member_id
        if line2_member_id is not None:
            body["line2MemberId"] = line2_member_id
        if custom_display_name is not None:
            body["customDisplayName"] = custom_display_name
        _missing = [f for f in ['line1MemberId', 'customDisplayName'] if f not in body or body[f] is None]
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



@app.command("show-handsets")
def show_handsets(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    handset_id: str = typer.Argument(help="handsetId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Specific DECT Network Handset Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets/{handset_id}"
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



_BODY_SKELETON_UPDATE_HANDSETS = '{"line1MemberId":"...","customDisplayName":"...","line2MemberId":"..."}'

@app.command("update-handsets")
def update_handsets(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    handset_id: str = typer.Argument(help="handsetId"),
    line1_member_id: str = typer.Option(None, "--line1-member-id", help="ID of the member on line1 of the handset. Members can be PEOPLE or PLACE."),
    line2_member_id: str = typer.Option(None, "--line2-member-id", help="ID of the member on line2 of the handset. Members can be PEOPLE, PLACE, or VIRTUAL_LINE."),
    custom_display_name: str = typer.Option(None, "--custom-display-name", help="Custom display name on the handset."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update DECT Network Handset\n\nExample --json-body:\n  '{"line1MemberId":"...","customDisplayName":"...","line2MemberId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_HANDSETS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets/{handset_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if line1_member_id is not None:
            body["line1MemberId"] = line1_member_id
        if line2_member_id is not None:
            body["line2MemberId"] = line2_member_id
        if custom_display_name is not None:
            body["customDisplayName"] = custom_display_name
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("delete-handsets-dect-networks")
def delete_handsets_dect_networks(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    handset_id: str = typer.Argument(help="handsetId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific DECT Network Handset Details."""
    if not force:
        typer.confirm(f"Delete {handset_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets/{handset_id}"
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
    else:
        typer.echo(f"Deleted: {handset_id}")



_BODY_SKELETON_DELETE_HANDSETS_DECT_NETWORKS_1 = '{"handsetIds":["..."],"deleteAll":true}'

@app.command("delete-handsets-dect-networks-1")
def delete_handsets_dect_networks_1(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    delete_all: bool = typer.Option(None, "--delete-all/--no-delete-all", help="If present the items array is ignored and all items in the context are deleted."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete multiple handsets\n\nExample --json-body:\n  '{"handsetIds":["..."],"deleteAll":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE_HANDSETS_DECT_NETWORKS_1), indent=2))
        raise typer.Exit(0)
    if not force:
        typer.confirm(f"Delete {dect_network_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets/"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if delete_all is not None:
            body["deleteAll"] = delete_all
    missing = [f for f in ['handsetIds'] if f not in body]
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
    else:
        typer.echo(f"Deleted: {dect_network_id}")



_BODY_SKELETON_CREATE_BULK = '{"items":[{"line1MemberId":"...","customDisplayName":"...","line2MemberId":"..."}]}'

@app.command("create-bulk")
def create_bulk(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a List of Handsets to a DECT Network\n\nExample --json-body:\n  '{"items":[{"line1MemberId":"...","customDisplayName":"...","line2MemberId":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets/bulk"
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
        if isinstance(result, dict) and "items" in result:
            typer.echo(f"Created: {result['items']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("list-dect-networks-people")
def list_dect_networks_people(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """GET List of DECT networks associated with a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/dectNetworks"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("list-dect-networks-workspaces")
def list_dect_networks_workspaces(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """GET List of DECT networks associated with a workspace."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/dectNetworks"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("list-available-members")
def list_available_members(
    member_name: str = typer.Option(None, "--member-name", help="Search (Contains) numbers based on member name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number."),
    extension: str = typer.Option(None, "--extension", help="Search (Contains) based on extension."),
    order: str = typer.Option(None, "--order", help="Sort the list of available members on the device in ascending order by name, using either last name `lname` or first name `fname`. Default sort is the last name in ascending order."),
    location_id: str = typer.Option(None, "--location-id", help="List members for the location ID."),
    exclude_virtual_line: str = typer.Option(None, "--exclude-virtual-line", help="If true, search results will exclude virtual lines in the member list. NOTE: Virtual lines cannot be assigned as the primary line."),
    usage_type: str = typer.Option(None, "--usage-type", help="Choices: DEVICE_OWNER, SHARED_LINE"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Available Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/availableMembers"
    params = {}
    if member_name is not None:
        params["memberName"] = member_name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    if order is not None:
        params["order"] = order
    if location_id is not None:
        params["locationId"] = location_id
    if exclude_virtual_line is not None:
        params["excludeVirtualLine"] = exclude_virtual_line
    if usage_type is not None:
        params["usageType"] = usage_type
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("generate-and-enable")
def generate_and_enable(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate and Enable DECT Serviceability Password."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/serviceabilityPassword/actions/generate/invoke"
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



@app.command("show-serviceability-password")
def show_serviceability_password(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get DECT Serviceability Password status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/serviceabilityPassword"
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



_BODY_SKELETON_UPDATE_SERVICEABILITY_PASSWORD = '{"enabled":true}'

@app.command("update-serviceability-password")
def update_serviceability_password(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="DECT serviceability password status. When `enabled` is set to `true`, the serviceability password can be used to manage DECT. When `enabled` is set to `false`, the serviceability password is disabled and the password owned and known by Cisco is required to perform serviceability and troubleshooting."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update DECT Serviceability Password status\n\nExample --json-body:\n  '{"enabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SERVICEABILITY_PASSWORD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/serviceabilityPassword"
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
    else:
        typer.echo(f"Updated.")


