import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling workspaces.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Location associated with the workspace. Values must originat"),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="Location associated with the workspace. Both values from the"),
    floor_id: str = typer.Option(None, "--floor-id", help="Floor associated with the workspace."),
    display_name: str = typer.Option(None, "--display-name", help="List workspaces by display name."),
    capacity: str = typer.Option(None, "--capacity", help="List workspaces with the given capacity. Must be -1 or highe"),
    type_param: str = typer.Option(None, "--type", help="Choices: notSet, focus, huddle, meetingRoom, open, desk, other"),
    calling: str = typer.Option(None, "--calling", help="Choices: freeCalling, hybridCalling, webexCalling, webexEdgeForDevices, thirdPartySipCalling, none"),
    supported_devices: str = typer.Option(None, "--supported-devices", help="Choices: collaborationDevices, phones"),
    calendar: str = typer.Option(None, "--calendar", help="Choices: none, google, microsoft"),
    device_hosted_meetings_enabled: str = typer.Option(None, "--device-hosted-meetings-enabled", help="List workspaces enabled for device hosted meetings."),
    device_platform: str = typer.Option(None, "--device-platform", help="Choices: cisco, microsoftTeamsRoom"),
    health_level: str = typer.Option(None, "--health-level", help="Choices: error, warning, info, ok"),
    include_devices: str = typer.Option(None, "--include-devices", help="Flag identifying whether to include the devices associated w"),
    include_capabilities: str = typer.Option(None, "--include-capabilities", help="Flag identifying whether to include the workspace capabiliti"),
    planned_maintenance: str = typer.Option(None, "--planned-maintenance", help="Choices: off, on, upcoming"),
    custom_attribute: str = typer.Option(None, "--custom-attribute", help="List workspaces with given custom attribute key."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Type', 'type'), ('Calling', 'calling.type')], limit=limit)



@app.command("create")
def create(
    display_name: str = typer.Option(None, "--display-name", help="(required) A friendly name for the workspace."),
    org_id: str = typer.Option(None, "--org-id", help="`OrgId` associated with the workspace. Only admin users of a"),
    location_id: str = typer.Option(None, "--location-id", help="Location associated with the workspace. Must be provided whe"),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="Legacy workspace location ID associated with the workspace."),
    floor_id: str = typer.Option(None, "--floor-id", help="Floor associated with the workspace."),
    capacity: str = typer.Option(None, "--capacity", help="How many people the workspace is suitable for. If set, must"),
    type_param: str = typer.Option(None, "--type", help="Choices: notSet, focus, huddle, meetingRoom, open, desk, other"),
    sip_address: str = typer.Option(None, "--sip-address", help="The `sipAddress` field can only be provided when calling typ"),
    notes: str = typer.Option(None, "--notes", help="Notes associated to the workspace."),
    hotdesking_status: str = typer.Option(None, "--hotdesking-status", help="Choices: on, off"),
    supported_devices: str = typer.Option(None, "--supported-devices", help="Choices: collaborationDevices, phones"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Workspace\n\nExample --json-body:\n  '{"displayName":"...","orgId":"...","locationId":"...","workspaceLocationId":"...","floorId":"...","capacity":0,"type":"notSet","sipAddress":"..."}'."""
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
        _missing = [f for f in ['displayName'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    workspace_id: str = typer.Argument(help="workspaceId"),
    include_devices: str = typer.Option(None, "--include-devices", help="Flag identifying whether to include the devices associated w"),
    include_capabilities: str = typer.Option(None, "--include-capabilities", help="Flag identifying whether to include the workspace capabiliti"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}"
    params = {}
    if include_devices is not None:
        params["includeDevices"] = include_devices
    if include_capabilities is not None:
        params["includeCapabilities"] = include_capabilities
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    workspace_id: str = typer.Argument(help="workspaceId"),
    display_name: str = typer.Option(None, "--display-name", help="A friendly name for the workspace."),
    location_id: str = typer.Option(None, "--location-id", help="Location associated with the workspace. Must be provided whe"),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="Legacy workspace location ID associated with the workspace."),
    floor_id: str = typer.Option(None, "--floor-id", help="Floor associated with the workspace."),
    capacity: str = typer.Option(None, "--capacity", help="How many people the workspace is suitable for. If set, must"),
    type_param: str = typer.Option(None, "--type", help="Choices: notSet, focus, huddle, meetingRoom, open, desk, other"),
    sip_address: str = typer.Option(None, "--sip-address", help="The `sipAddress` field can only be provided when calling typ"),
    notes: str = typer.Option(None, "--notes", help="Notes associated to the workspace."),
    hotdesking_status: str = typer.Option(None, "--hotdesking-status", help="Choices: on, off"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Workspace\n\nExample --json-body:\n  '{"displayName":"...","locationId":"...","workspaceLocationId":"...","floorId":"...","capacity":0,"type":"notSet","calendar":{"type":"...","emailAddress":"...","resourceGroupId":"..."},"sipAddress":"..."}'."""
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
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {workspace_id}")



@app.command("show-capabilities")
def show_capabilities(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace Capabilities."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}/capabilities"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)


