import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling locations.")


@app.command("list")
def cmd_list(
    name: str = typer.Option(None, "--name", help="List locations whose name contains this string (case-insensi"),
    id_param: str = typer.Option(None, "--id", help="List locations by ID."),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of location in the response."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    if max is not None:
        params["max"] = max
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
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    name: str = typer.Option(..., "--name", help="The name of the location. Supports up to 256 characters, but"),
    time_zone: str = typer.Option(..., "--time-zone", help="Time zone associated with this location, refer to this link"),
    preferred_language: str = typer.Option(..., "--preferred-language", help="Default email language."),
    announcement_language: str = typer.Option(..., "--announcement-language", help="Location's phone announcement language."),
    latitude: str = typer.Option(None, "--latitude", help="Latitude"),
    longitude: str = typer.Option(None, "--longitude", help="Longitude"),
    notes: str = typer.Option(None, "--notes", help="Notes"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations"
    if json_body:
        body = json.loads(json_body)
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
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}"
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
    name: str = typer.Option(None, "--name", help="The name of the location. Supports up to 256 characters, but"),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone associated with this location, refer to this link"),
    preferred_language: str = typer.Option(None, "--preferred-language", help="Default email language."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if time_zone is not None:
            body["timeZone"] = time_zone
        if preferred_language is not None:
            body["preferredLanguage"] = preferred_language
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
    location_id: str = typer.Argument(help="locationId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Location."""
    if not force:
        typer.confirm(f"Delete {location_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {location_id}")



@app.command("list-floors")
def list_floors(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Location Floors."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors"
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
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-floors")
def create_floors(
    location_id: str = typer.Argument(help="locationId"),
    floor_number: str = typer.Option(..., "--floor-number", help="The floor number."),
    display_name: str = typer.Option(None, "--display-name", help="The floor display name."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Location Floor."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if floor_number is not None:
            body["floorNumber"] = floor_number
        if display_name is not None:
            body["displayName"] = display_name
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



@app.command("show-floors")
def show_floors(
    location_id: str = typer.Argument(help="locationId"),
    floor_id: str = typer.Argument(help="floorId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Floor Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors/{floor_id}"
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



@app.command("update-floors")
def update_floors(
    location_id: str = typer.Argument(help="locationId"),
    floor_id: str = typer.Argument(help="floorId"),
    floor_number: str = typer.Option(None, "--floor-number", help="The floor number."),
    display_name: str = typer.Option(None, "--display-name", help="The floor display name."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location Floor."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors/{floor_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if floor_number is not None:
            body["floorNumber"] = floor_number
        if display_name is not None:
            body["displayName"] = display_name
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



@app.command("delete-floors")
def delete_floors(
    location_id: str = typer.Argument(help="locationId"),
    floor_id: str = typer.Argument(help="floorId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Location Floor."""
    if not force:
        typer.confirm(f"Delete {floor_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/locations/{location_id}/floors/{floor_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {floor_id}")


