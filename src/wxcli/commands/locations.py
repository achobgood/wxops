import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling locations.")


@app.command("list", short_help="List Locations.")
def cmd_list(
    name: str = typer.Option(None, "--name", help="List locations whose name contains this string (case-insensitive)."),
    id_param: str = typer.Option(None, "--id", help="List locations by ID."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Locations."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations"
    params = {}
    if name is not None:
        params["name"] = name
    if id_param is not None:
        params["id"] = id_param
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
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('City', 'address.city'), ('State', 'address.state'), ('Time Zone', 'timeZone')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","timeZone":"...","preferredLanguage":"...","announcementLanguage":"...","address":{"address1":"...","city":"...","state":"...","postalCode":"...","country":"...","address2":"..."},"latitude":"...","longitude":"...","notes":"..."}'

@app.command("create", short_help="Create a Location.")
def create(
    name: str = typer.Option(None, "--name", help="(required) The name of the location. Supports up to 256 characters, but locations enabled for Webex Calling are limited to 80 characters maximum."),
    time_zone: str = typer.Option(None, "--time-zone", help="(required) Time zone associated with this location, refer to this link (https://developer.webex.com/docs/api/guides/webex-for-broadworks-developers-guide#webex-meetings-site-timezone) for format."),
    preferred_language: str = typer.Option(None, "--preferred-language", help="(required) Default email language."),
    announcement_language: str = typer.Option(None, "--announcement-language", help="(required) Location's phone announcement language."),
    latitude: str = typer.Option(None, "--latitude", help="Latitude"),
    longitude: str = typer.Option(None, "--longitude", help="Longitude"),
    notes: str = typer.Option(None, "--notes", help="Notes"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Location.\n\n\b\nExample: wxcli locations create --name NAME --time-zone TIME_ZONE --preferred-language PREFERRED_LANGUAGE --announcement-language ANNOUNCEMENT_LANGUAGE\n\n\b\nExample --json-body: '{"name":"...","timeZone":"...","preferredLanguage":"...","announcementLanguage":"...","address":{"address1":"...","city":"...","state":"...","postalCode":"...","country":"...","address2":"..."},"latitude":"...","longitude":"...","notes":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations"
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
        if time_zone is not None:
            body["timeZone"] = time_zone
        if preferred_language is not None:
            body["preferredLanguage"] = preferred_language
        if announcement_language is not None:
            body["announcementLanguage"] = announcement_language
        if latitude is not None:
            body["latitude"] = latitude
        if longitude is not None:
            body["longitude"] = longitude
        if notes is not None:
            body["notes"] = notes
        _missing = [f for f in ['name', 'timeZone', 'preferredLanguage', 'announcementLanguage'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Location Details.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Details.\n\n\b\nExample: wxcli locations show LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}"
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



_BODY_SKELETON_UPDATE = '{"name":"...","timeZone":"...","preferredLanguage":"...","address":{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}}'

@app.command("update", short_help="Update a Location.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    name: str = typer.Option(None, "--name", help="The name of the location. Supports up to 256 characters, but locations enabled for Webex Calling are limited to 80 characters maximum."),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone associated with this location, refer to this link (https://developer.webex.com/docs/api/guides/webex-for-broadworks-developers-guide#webex-meetings-site-timezone) for format."),
    preferred_language: str = typer.Option(None, "--preferred-language", help="Default email language."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location.\n\n\b\nExample: wxcli locations update LOCATION_ID\n\n\b\nExample --json-body: '{"name":"...","timeZone":"...","preferredLanguage":"...","address":{"address1":"...","address2":"...","city":"...","state":"...","postalCode":"...","country":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}"
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
        if time_zone is not None:
            body["timeZone"] = time_zone
        if preferred_language is not None:
            body["preferredLanguage"] = preferred_language
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



@app.command("delete", short_help="Delete Location.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Location.\n\n\b\nExample: wxcli locations delete LOCATION_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {location_id}?", abort=True)
    url = f"https://webexapis.com/v1/locations/{location_id}"
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
        typer.echo(f"Deleted: {location_id}")
    else:
        emit({"status": "deleted", "id": location_id}, output=output, fields=fields)



@app.command("list-floors", short_help="List Location Floors.")
def list_floors(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Location Floors.\n\n\b\nExample: wxcli locations list-floors LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Location ID', 'locationId'), ('Floor Number', 'floorNumber')], limit=limit)



_BODY_SKELETON_CREATE_FLOORS = '{"floorNumber":0,"displayName":"..."}'

@app.command("create-floors", short_help="Create a Location Floor.")
def create_floors(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    floor_number: str = typer.Option(None, "--floor-number", help="(required) The floor number."),
    display_name: str = typer.Option(None, "--display-name", help="The floor display name."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Location Floor.\n\n\b\nExample: wxcli locations create-floors LOCATION_ID --floor-number FLOOR_NUMBER\n\n\b\nExample --json-body: '{"floorNumber":0,"displayName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_FLOORS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors"
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



@app.command("show-floors", short_help="Get Location Floor Details.")
def show_floors(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    floor_id: str = typer.Argument(help="Webex WORKSPACE_LOCATION_FLOOR id, from: wxcli locations list-floors"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Floor Details.\n\n\b\nExample: wxcli locations show-floors LOCATION_ID FLOOR_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors/{floor_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_FLOORS = '{"floorNumber":0,"displayName":"..."}'

@app.command("update-floors", short_help="Update a Location Floor.")
def update_floors(
    location_id: str = typer.Argument(help="Webex WORKSPACE_LOCATION id, from: wxcli locations list"),
    floor_id: str = typer.Argument(help="Webex WORKSPACE_LOCATION_FLOOR id, from: wxcli locations list-floors"),
    floor_number: str = typer.Option(None, "--floor-number", help="The floor number."),
    display_name: str = typer.Option(None, "--display-name", help="The floor display name."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location Floor.\n\n\b\nExample: wxcli locations update-floors LOCATION_ID FLOOR_ID --floor-number FLOOR_NUMBER\n\n\b\nExample --json-body: '{"floorNumber":0,"displayName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_FLOORS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors/{floor_id}"
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



@app.command("delete-floors", short_help="Delete a Location Floor.")
def delete_floors(
    location_id: str = typer.Argument(help="Webex WORKSPACE_LOCATION id, from: wxcli locations list"),
    floor_id: str = typer.Argument(help="Webex WORKSPACE_LOCATION_FLOOR id, from: wxcli locations list-floors"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Location Floor.\n\n\b\nExample: wxcli locations delete-floors LOCATION_ID FLOOR_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {floor_id}?", abort=True)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors/{floor_id}"
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


