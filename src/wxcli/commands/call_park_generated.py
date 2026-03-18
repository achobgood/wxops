import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling call-park.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of call parks returned to this maximum coun"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching call"),
    order: str = typer.Option(None, "--order", help="Sort the list of call parks by name, either ASC or DSC. Defa"),
    name: str = typer.Option(None, "--name", help="Return the list of call parks that contains the given name."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Parks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if order is not None:
        params["order"] = order
    if name is not None:
        params["name"] = name
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
    items = result.get("callParks", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(..., "--name", help=""),
    park_on_agents_enabled: bool = typer.Option(None, "--park-on-agents-enabled/--no-park-on-agents-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Call Park."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        body.setdefault('recall', {'option': 'ALERT_PARKING_USER_ONLY'})
        if park_on_agents_enabled is not None:
            body["parkOnAgentsEnabled"] = park_on_agents_enabled
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
    call_park_id: str = typer.Argument(help="callParkId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Park."""
    if not force:
        typer.confirm(f"Delete {call_park_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/{call_park_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {call_park_id}")



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    call_park_id: str = typer.Argument(help="callParkId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Park."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/{call_park_id}"
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
    call_park_id: str = typer.Argument(help="callParkId"),
    name: str = typer.Option(None, "--name", help=""),
    park_on_agents_enabled: bool = typer.Option(None, "--park-on-agents-enabled/--no-park-on-agents-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Park."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/{call_park_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if park_on_agents_enabled is not None:
            body["parkOnAgentsEnabled"] = park_on_agents_enabled
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



@app.command("list-available-users")
def list_available_users(
    location_id: str = typer.Argument(help="locationId"),
    call_park_name: str = typer.Option(None, "--call-park-name", help="Only return available agents from call parks with the matchi"),
    max: str = typer.Option(None, "--max", help="Limit the number of available agents returned to this maximu"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching avail"),
    name: str = typer.Option(None, "--name", help="Only return available agents with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return available agents with the matching primary numbe"),
    order: str = typer.Option(None, "--order", help="Order the available agents according to the designated field"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get available agents from Call Parks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/availableUsers"
    params = {}
    if call_park_name is not None:
        params["callParkName"] = call_park_name
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
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
    items = result.get("availableUsers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-available-recall-hunt-groups")
def list_available_recall_hunt_groups(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of available recall hunt groups returned to"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching avail"),
    name: str = typer.Option(None, "--name", help="Only return available recall hunt groups with the matching n"),
    order: str = typer.Option(None, "--order", help="Order the available recall hunt groups according to the desi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get available recall hunt groups from Call Parks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/availableRecallHuntGroups"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if order is not None:
        params["order"] = order
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
    items = result.get("availableRecallHuntGroups", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("show-settings")
def show_settings(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Park Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/settings"
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



@app.command("update-settings")
def update_settings(
    location_id: str = typer.Argument(help="locationId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Park settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/settings"
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



@app.command("list-call-park-extensions")
def list_call_park_extensions(
    location_id: str = typer.Option(None, "--location-id", help="Only return call park extensions with matching location ID."),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objec"),
    extension: str = typer.Option(None, "--extension", help="Only return call park extensions with the matching extension"),
    location_name: str = typer.Option(None, "--location-name", help="Only return call park extensions with the matching extension"),
    name: str = typer.Option(None, "--name", help="Only return call park extensions with the matching name."),
    order: str = typer.Option(None, "--order", help="Order the available agents according to the designated field"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Park Extensions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callParkExtensions"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if extension is not None:
        params["extension"] = extension
    if location_name is not None:
        params["locationName"] = location_name
    if name is not None:
        params["name"] = name
    if order is not None:
        params["order"] = order
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
    items = result.get("callParkExtensions", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("show-call-park-extensions")
def show_call_park_extensions(
    location_id: str = typer.Argument(help="locationId"),
    call_park_extension_id: str = typer.Argument(help="callParkExtensionId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Park Extension."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParkExtensions/{call_park_extension_id}"
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



@app.command("delete-call-park-extensions")
def delete_call_park_extensions(
    location_id: str = typer.Argument(help="locationId"),
    call_park_extension_id: str = typer.Argument(help="callParkExtensionId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Park Extension."""
    if not force:
        typer.confirm(f"Delete {call_park_extension_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParkExtensions/{call_park_extension_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {call_park_extension_id}")



@app.command("update-call-park-extensions")
def update_call_park_extensions(
    location_id: str = typer.Argument(help="locationId"),
    call_park_extension_id: str = typer.Argument(help="callParkExtensionId"),
    name: str = typer.Option(None, "--name", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Park Extension."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParkExtensions/{call_park_extension_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if extension is not None:
            body["extension"] = extension
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



@app.command("create-call-park-extensions")
def create_call_park_extensions(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(..., "--name", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Call Park Extension."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParkExtensions"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if extension is not None:
            body["extension"] = extension
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


