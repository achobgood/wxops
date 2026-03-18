import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling workspaces.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Location associated with the workspace. Values must originat"),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="Location associated with the workspace. Both values from the"),
    floor_id: str = typer.Option(None, "--floor-id", help="Floor associated with the workspace."),
    display_name: str = typer.Option(None, "--display-name", help="List workspaces by display name."),
    capacity: str = typer.Option(None, "--capacity", help="List workspaces with the given capacity. Must be -1 or highe"),
    type_param: str = typer.Option(None, "--type", help="List workspaces by type."),
    start: str = typer.Option(None, "--start", help="Offset. Default is 0."),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of workspaces in the response."),
    calling: str = typer.Option(None, "--calling", help="List workspaces by calling type."),
    supported_devices: str = typer.Option(None, "--supported-devices", help="List workspaces by supported devices."),
    calendar: str = typer.Option(None, "--calendar", help="List workspaces by calendar type."),
    device_hosted_meetings_enabled: str = typer.Option(None, "--device-hosted-meetings-enabled", help="List workspaces enabled for device hosted meetings."),
    device_platform: str = typer.Option(None, "--device-platform", help="List workspaces by device platform."),
    health_level: str = typer.Option(None, "--health-level", help="List workspaces by health level."),
    include_devices: str = typer.Option(None, "--include-devices", help="Flag identifying whether to include the devices associated w"),
    include_capabilities: str = typer.Option(None, "--include-capabilities", help="Flag identifying whether to include the workspace capabiliti"),
    planned_maintenance: str = typer.Option(None, "--planned-maintenance", help="List workspaces with given maintenance mode."),
    custom_attribute: str = typer.Option(None, "--custom-attribute", help="List workspaces with given custom attribute key."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Workspaces."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if workspace_location_id is not None:
        params["workspaceLocationId"] = workspace_location_id
    if floor_id is not None:
        params["floorId"] = floor_id
    if display_name is not None:
        params["displayName"] = display_name
    if capacity is not None:
        params["capacity"] = capacity
    if type_param is not None:
        params["type"] = type_param
    if start is not None:
        params["start"] = start
    if max is not None:
        params["max"] = max
    if calling is not None:
        params["calling"] = calling
    if supported_devices is not None:
        params["supportedDevices"] = supported_devices
    if calendar is not None:
        params["calendar"] = calendar
    if device_hosted_meetings_enabled is not None:
        params["deviceHostedMeetingsEnabled"] = device_hosted_meetings_enabled
    if device_platform is not None:
        params["devicePlatform"] = device_platform
    if health_level is not None:
        params["healthLevel"] = health_level
    if include_devices is not None:
        params["includeDevices"] = include_devices
    if include_capabilities is not None:
        params["includeCapabilities"] = include_capabilities
    if planned_maintenance is not None:
        params["plannedMaintenance"] = planned_maintenance
    if custom_attribute is not None:
        params["customAttribute"] = custom_attribute
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
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Type', 'type'), ('Calling', 'calling.type')], limit=limit)



@app.command("create")
def create(
    display_name: str = typer.Option(None, "--display-name", help=""),
    org_id: str = typer.Option(None, "--org-id", help=""),
    location_id: str = typer.Option(None, "--location-id", help=""),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help=""),
    floor_id: str = typer.Option(None, "--floor-id", help=""),
    capacity: str = typer.Option(None, "--capacity", help=""),
    type_param: str = typer.Option(None, "--type", help=""),
    sip_address: str = typer.Option(None, "--sip-address", help=""),
    notes: str = typer.Option(None, "--notes", help=""),
    hotdesking_status: str = typer.Option(None, "--hotdesking-status", help=""),
    supported_devices: str = typer.Option(None, "--supported-devices", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Workspace."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if display_name is not None:
            body["displayName"] = display_name
        if org_id is not None:
            body["orgId"] = org_id
        if location_id is not None:
            body["locationId"] = location_id
        if workspace_location_id is not None:
            body["workspaceLocationId"] = workspace_location_id
        if floor_id is not None:
            body["floorId"] = floor_id
        if capacity is not None:
            body["capacity"] = capacity
        if type_param is not None:
            body["type"] = type_param
        if sip_address is not None:
            body["sipAddress"] = sip_address
        if notes is not None:
            body["notes"] = notes
        if hotdesking_status is not None:
            body["hotdeskingStatus"] = hotdesking_status
        if supported_devices is not None:
            body["supportedDevices"] = supported_devices
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



@app.command("list-workspaces")
def list_workspaces(
    workspace_id: str = typer.Argument(help="workspaceId"),
    include_devices: str = typer.Option(None, "--include-devices", help="Flag identifying whether to include the devices associated w"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}/"
    params = {}
    if include_devices is not None:
        params["includeDevices"] = include_devices
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



@app.command("update")
def update(
    workspace_id: str = typer.Argument(help="workspaceId"),
    display_name: str = typer.Option(None, "--display-name", help=""),
    location_id: str = typer.Option(None, "--location-id", help=""),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help=""),
    floor_id: str = typer.Option(None, "--floor-id", help=""),
    capacity: str = typer.Option(None, "--capacity", help=""),
    type_param: str = typer.Option(None, "--type", help=""),
    sip_address: str = typer.Option(None, "--sip-address", help=""),
    notes: str = typer.Option(None, "--notes", help=""),
    hotdesking_status: str = typer.Option(None, "--hotdesking-status", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Workspace."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if display_name is not None:
            body["displayName"] = display_name
        if location_id is not None:
            body["locationId"] = location_id
        if workspace_location_id is not None:
            body["workspaceLocationId"] = workspace_location_id
        if floor_id is not None:
            body["floorId"] = floor_id
        if capacity is not None:
            body["capacity"] = capacity
        if type_param is not None:
            body["type"] = type_param
        if sip_address is not None:
            body["sipAddress"] = sip_address
        if notes is not None:
            body["notes"] = notes
        if hotdesking_status is not None:
            body["hotdeskingStatus"] = hotdesking_status
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
    workspace_id: str = typer.Argument(help="workspaceId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Workspace."""
    if not force:
        typer.confirm(f"Delete {workspace_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {workspace_id}")



@app.command("list-capabilities")
def list_capabilities(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace Capabilities."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}/capabilities"
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
    items = result.get("capabilities", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}"
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


