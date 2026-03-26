import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.errors import handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling dect-devices-settings.")


@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) Name of the DECT network. Min and max length supported for t"),
    display_name: str = typer.Option(None, "--display-name", help="Add a default name (11 characters max) to display for all ha"),
    model: str = typer.Option(None, "--model", help="(required) Choices: DMS Cisco DBS110, Cisco DECT 110 Base, DMS Cisco DBS210, Cisco DECT 210 Base"),
    default_access_code_enabled: bool = typer.Option(None, "--default-access-code-enabled/--no-default-access-code-enabled", help="(required) If set to true, need to provide a default access code that w"),
    default_access_code: str = typer.Option(None, "--default-access-code", help="(required) If `defaultAccessCodeEnabled` is set to true, then provide a"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a DECT Network."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks"
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
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "dectNetworkId" in result:
        typer.echo(f"Created: {result['dectNetworkId']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list")
def cmd_list(
    name: str = typer.Option(None, "--name", help="List of DECT networks with this name."),
    location_id: str = typer.Option(None, "--location-id", help="List of DECT networks at this location."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("dectNetworks", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    name: str = typer.Option(None, "--name", help="Name of the DECT network. This should be unique across the l"),
    display_name: str = typer.Option(None, "--display-name", help="DECT network name that will be displayed on the handset."),
    default_access_code_enabled: bool = typer.Option(None, "--default-access-code-enabled/--no-default-access-code-enabled", help="Default access code is enabled. If true, the default access"),
    default_access_code: str = typer.Option(None, "--default-access-code", help="Default access code for the DECT network. The default access"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update DECT Network."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}"
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
        if display_name is not None:
            body["displayName"] = display_name
        if default_access_code_enabled is not None:
            body["defaultAccessCodeEnabled"] = default_access_code_enabled
        if default_access_code is not None:
            body["defaultAccessCode"] = default_access_code
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
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
        api.session.rest_delete(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {dect_network_id}")



@app.command("list-base-stations")
def list_base_stations(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("baseStations", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("create-base-stations")
def create_base_stations(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Multiple Base Stations\n\nExample --json-body:\n  '{"baseStationMacs":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/baseStations"
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
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "baseStations" in result:
        typer.echo(f"Created: {result['baseStations']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("delete-base-stations-dect-networks")
def delete_base_stations_dect_networks(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
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
        api.session.rest_delete(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {dect_network_id}")



@app.command("show-base-stations")
def show_base_stations(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    base_station_id: str = typer.Argument(help="baseStationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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



@app.command("delete-base-stations-dect-networks-1")
def delete_base_stations_dect_networks_1(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    base_station_id: str = typer.Argument(help="baseStationId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
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
        api.session.rest_delete(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {base_station_id}")



@app.command("list-handsets")
def list_handsets(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    basestation_id: str = typer.Option(None, "--basestation-id", help="Search handset details in the specified DECT base station ID"),
    member_id: str = typer.Option(None, "--member-id", help="ID of the member of the handset. Members can be of type PEOP"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("handsets", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("create-handsets")
def create_handsets(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    line1_member_id: str = typer.Option(None, "--line1-member-id", help="(required) ID of the member on line1 of the handset. Members can be PEO"),
    line2_member_id: str = typer.Option(None, "--line2-member-id", help="ID of the member on line2 of the handset. Members can be PEO"),
    custom_display_name: str = typer.Option(None, "--custom-display-name", help="(required) Custom display name on the handset. Min and max length suppo"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a Handset to a DECT Network."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-handsets")
def show_handsets(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    handset_id: str = typer.Argument(help="handsetId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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



@app.command("update-handsets")
def update_handsets(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    handset_id: str = typer.Argument(help="handsetId"),
    line1_member_id: str = typer.Option(None, "--line1-member-id", help="ID of the member on line1 of the handset. Members can be PEO"),
    line2_member_id: str = typer.Option(None, "--line2-member-id", help="ID of the member on line2 of the handset. Members can be PEO"),
    custom_display_name: str = typer.Option(None, "--custom-display-name", help="Custom display name on the handset."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update DECT Network Handset."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets/{handset_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-handsets-dect-networks")
def delete_handsets_dect_networks(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    handset_id: str = typer.Argument(help="handsetId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
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
        api.session.rest_delete(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {handset_id}")



@app.command("delete-handsets-dect-networks-1")
def delete_handsets_dect_networks_1(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete multiple handsets."""
    if not force:
        typer.confirm(f"Delete {dect_network_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets/"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {dect_network_id}")



@app.command("create-bulk")
def create_bulk(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a List of Handsets to a DECT Network\n\nExample --json-body:\n  '{"items":[{"line1MemberId":"...","line2MemberId":"...","customDisplayName":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/handsets/bulk"
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
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "items" in result:
        typer.echo(f"Created: {result['items']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-dect-networks-people")
def list_dect_networks_people(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("dectNetworks", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("list-dect-networks-workspaces")
def list_dect_networks_workspaces(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("dectNetworks", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("list-available-members")
def list_available_members(
    start: str = typer.Option(None, "--start", help="Specifies the offset from the first result that you want to"),
    max: str = typer.Option(None, "--max", help="Specifies the maximum number of records that you want to fet"),
    member_name: str = typer.Option(None, "--member-name", help="Search (Contains) numbers based on member name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number."),
    extension: str = typer.Option(None, "--extension", help="Search (Contains) based on extension."),
    order: str = typer.Option(None, "--order", help="Sort the list of available members on the device in ascendin"),
    location_id: str = typer.Option(None, "--location-id", help="List members for the location ID."),
    exclude_virtual_line: str = typer.Option(None, "--exclude-virtual-line", help="If true, search results will exclude virtual lines in the me"),
    usage_type: str = typer.Option(None, "--usage-type", help="Choices: DEVICE_OWNER, SHARED_LINE"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search Available Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/availableMembers"
    params = {}
    if start is not None:
        params["start"] = start
    if max is not None:
        params["max"] = max
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("members", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Model', 'model')], limit=limit)



@app.command("generate-and-enable")
def generate_and_enable(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
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
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    print_json(result)



@app.command("show-serviceability-password")
def show_serviceability_password(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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



@app.command("update-serviceability-password")
def update_serviceability_password(
    location_id: str = typer.Argument(help="locationId"),
    dect_network_id: str = typer.Argument(help="dectNetworkId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="DECT serviceability password status. When `enabled` is set t"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update DECT Serviceability Password status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/dectNetworks/{dect_network_id}/serviceabilityPassword"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")


