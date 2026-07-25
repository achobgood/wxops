import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling workspace-locations.")


@app.command("list")
def cmd_list(
    display_name: str = typer.Option(None, "--display-name", help="Location display name."),
    address: str = typer.Option(None, "--address", help="Location address."),
    country_code: str = typer.Option(None, "--country-code", help="Location country code (ISO 3166-1)."),
    city_name: str = typer.Option(None, "--city-name", help="Location city name."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Workspace Locations."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations"
    params = {}
    if display_name is not None:
        params["displayName"] = display_name
    if address is not None:
        params["address"] = address
    if country_code is not None:
        params["countryCode"] = country_code
    if city_name is not None:
        params["cityName"] = city_name
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('City', 'cityName')], limit=limit)



_BODY_SKELETON_CREATE = '{"displayName":"...","address":"...","countryCode":"...","latitude":0,"longitude":0,"cityName":"...","notes":"..."}'

@app.command("create")
def create(
    display_name: str = typer.Option(None, "--display-name", help="(required) A friendly name for the location."),
    address: str = typer.Option(None, "--address", help="(required) The location address."),
    country_code: str = typer.Option(None, "--country-code", help="(required) The location country code (ISO 3166-1)."),
    city_name: str = typer.Option(None, "--city-name", help="The location city name."),
    latitude: str = typer.Option(None, "--latitude", help="(required) The location latitude."),
    longitude: str = typer.Option(None, "--longitude", help="(required) The location longitude."),
    notes: str = typer.Option(None, "--notes", help="Notes associated with the location."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Workspace Location\n\nExample --json-body:\n  '{"displayName":"...","address":"...","countryCode":"...","latitude":0,"longitude":0,"cityName":"...","notes":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if display_name is not None:
            body["displayName"] = display_name
        if address is not None:
            body["address"] = address
        if country_code is not None:
            body["countryCode"] = country_code
        if city_name is not None:
            body["cityName"] = city_name
        if latitude is not None:
            body["latitude"] = latitude
        if longitude is not None:
            body["longitude"] = longitude
        if notes is not None:
            body["notes"] = notes
        _missing = [f for f in ['displayName', 'address', 'countryCode', 'latitude', 'longitude'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Workspace Location Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations/{location_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"displayName":"...","address":"...","countryCode":"...","latitude":0,"longitude":0,"id":"...","cityName":"...","notes":"..."}'

@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    id_param: str = typer.Option(None, "--id", help="Unique identifier for the location."),
    display_name: str = typer.Option(None, "--display-name", help="A friendly name for the location."),
    address: str = typer.Option(None, "--address", help="The location address."),
    country_code: str = typer.Option(None, "--country-code", help="The location country code (ISO 3166-1)."),
    city_name: str = typer.Option(None, "--city-name", help="The location city name."),
    latitude: str = typer.Option(None, "--latitude", help="The location latitude."),
    longitude: str = typer.Option(None, "--longitude", help="The location longitude."),
    notes: str = typer.Option(None, "--notes", help="Notes associated with the location."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Workspace Location\n\nExample --json-body:\n  '{"displayName":"...","address":"...","countryCode":"...","latitude":0,"longitude":0,"id":"...","cityName":"...","notes":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations/{location_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        if display_name is not None:
            body["displayName"] = display_name
        if address is not None:
            body["address"] = address
        if country_code is not None:
            body["countryCode"] = country_code
        if city_name is not None:
            body["cityName"] = city_name
        if latitude is not None:
            body["latitude"] = latitude
        if longitude is not None:
            body["longitude"] = longitude
        if notes is not None:
            body["notes"] = notes
    try:
        result = api.session.rest_put(url, json=body)
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



@app.command("delete")
def delete(
    location_id: str = typer.Argument(help="locationId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Workspace Location."""
    if not force:
        typer.confirm(f"Delete {location_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations/{location_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {location_id}")
    else:
        emit({"status": "deleted", "id": location_id}, output=output, fields=fields)



@app.command("list-floors")
def list_floors(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Workspace Location Floors."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations/{location_id}/floors"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('City', 'cityName')], limit=limit)



_BODY_SKELETON_CREATE_FLOORS = '{"floorNumber":0,"displayName":"..."}'

@app.command("create-floors")
def create_floors(
    location_id: str = typer.Argument(help="locationId"),
    floor_number: str = typer.Option(None, "--floor-number", help="(required) The floor number."),
    display_name: str = typer.Option(None, "--display-name", help="The floor display name."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Workspace Location Floor\n\nExample --json-body:\n  '{"floorNumber":0,"displayName":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_FLOORS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations/{location_id}/floors"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if floor_number is not None:
            body["floorNumber"] = floor_number
        if display_name is not None:
            body["displayName"] = display_name
        _missing = [f for f in ['floorNumber'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-floors")
def show_floors(
    location_id: str = typer.Argument(help="locationId"),
    floor_id: str = typer.Argument(help="floorId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Workspace Location Floor Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations/{location_id}/floors/{floor_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_FLOORS = '{"floorNumber":0,"displayName":"..."}'

@app.command("update-floors")
def update_floors(
    location_id: str = typer.Argument(help="locationId"),
    floor_id: str = typer.Argument(help="floorId"),
    floor_number: str = typer.Option(None, "--floor-number", help="The floor number."),
    display_name: str = typer.Option(None, "--display-name", help="The floor display name."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Workspace Location Floor\n\nExample --json-body:\n  '{"floorNumber":0,"displayName":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_FLOORS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations/{location_id}/floors/{floor_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if floor_number is not None:
            body["floorNumber"] = floor_number
        if display_name is not None:
            body["displayName"] = display_name
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": floor_id}, output=output, fields=fields)



@app.command("delete-floors")
def delete_floors(
    location_id: str = typer.Argument(help="locationId"),
    floor_id: str = typer.Argument(help="floorId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Workspace Location Floor."""
    if not force:
        typer.confirm(f"Delete {floor_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceLocations/{location_id}/floors/{floor_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {floor_id}")
    else:
        emit({"status": "deleted", "id": floor_id}, output=output, fields=fields)


