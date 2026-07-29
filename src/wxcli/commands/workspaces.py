import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling workspaces.")


@app.command("list", short_help="List Workspaces.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Location associated with the workspace. Values must originate from the /locations API and not the legacy /workspaceLocations API."),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="Location associated with the workspace. Both values from the /locations API and the legacy /workspaceLocations API are supported. This field is deprecated and integrations should prefer `locationId` going forward."),
    floor_id: str = typer.Option(None, "--floor-id", help="Floor associated with the workspace."),
    display_name: str = typer.Option(None, "--display-name", help="List workspaces by display name."),
    capacity: str = typer.Option(None, "--capacity", help="List workspaces with the given capacity. Must be -1 or higher. A value of -1 lists workspaces with no capacity set."),
    type_param: str = typer.Option(None, "--type", help="Choices: notSet, focus, huddle, meetingRoom, open, desk, other"),
    calling: str = typer.Option(None, "--calling", help="Choices: freeCalling, hybridCalling, webexCalling, webexEdgeForDevices, thirdPartySipCalling, none"),
    supported_devices: str = typer.Option(None, "--supported-devices", help="Choices: collaborationDevices, phones"),
    calendar: str = typer.Option(None, "--calendar", help="Choices: none, google, microsoft"),
    device_hosted_meetings_enabled: str = typer.Option(None, "--device-hosted-meetings-enabled", help="List workspaces enabled for device hosted meetings."),
    device_platform: str = typer.Option(None, "--device-platform", help="Choices: cisco, microsoftTeamsRoom"),
    health_level: str = typer.Option(None, "--health-level", help="Choices: error, warning, info, ok"),
    include_devices: str = typer.Option(None, "--include-devices", help="Flag identifying whether to include the devices associated with the workspace in the response."),
    include_capabilities: str = typer.Option(None, "--include-capabilities", help="Flag identifying whether to include the workspace capabilities in the response."),
    planned_maintenance: str = typer.Option(None, "--planned-maintenance", help="Choices: off, on, upcoming"),
    custom_attribute: str = typer.Option(None, "--custom-attribute", help="List workspaces with given custom attribute key."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Type', 'type'), ('Calling', 'calling.type')], limit=limit)



_BODY_SKELETON_CREATE = '{"displayName":"...","orgId":"...","locationId":"...","workspaceLocationId":"...","floorId":"...","capacity":0,"type":"notSet","sipAddress":"...","calling":{"type":"freeCalling","webexCalling":{"phoneNumber":"...","extension":"...","locationId":"...","licenses":["..."]}},"calendar":{"type":"...","emailAddress":"...","resourceGroupId":"..."},"notes":"...","hotdeskingStatus":"on","deviceHostedMeetings":{"enabled":true,"siteUrl":"..."},"supportedDevices":"collaborationDevices","indoorNavigation":{"url":"..."}}'

@app.command("create", short_help="Create a Workspace.")
def create(
    display_name: str = typer.Option(None, "--display-name", help="(required) A friendly name for the workspace."),
    org_id: str = typer.Option(None, "--org-id", help="`OrgId` associated with the workspace. Only admin users of another organization (such as partners) may use this parameter."),
    location_id: str = typer.Option(None, "--location-id", help="Location associated with the workspace. Must be provided when the `floorId` is set."),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="Legacy workspace location ID associated with the workspace. Prefer `locationId`."),
    floor_id: str = typer.Option(None, "--floor-id", help="Floor associated with the workspace."),
    capacity: str = typer.Option(None, "--capacity", help="How many people the workspace is suitable for. If set, must be 0 or higher."),
    type_param: str = typer.Option(None, "--type", help="Choices: notSet, focus, huddle, meetingRoom, open, desk, other"),
    sip_address: str = typer.Option(None, "--sip-address", help="The `sipAddress` field can only be provided when calling type is `thirdPartySipCalling`."),
    notes: str = typer.Option(None, "--notes", help="Notes associated to the workspace."),
    hotdesking_status: str = typer.Option(None, "--hotdesking-status", help="Choices: on, off"),
    supported_devices: str = typer.Option(None, "--supported-devices", help="Choices: collaborationDevices, phones"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Workspace.\n\n\b\nExample: wxcli workspaces create --display-name DISPLAY_NAME\n\n\b\nExample --json-body: '{"displayName":"...","orgId":"...","locationId":"...","workspaceLocationId":"...","floorId":"...","capacity":0,"type":"notSet","sipAddress":"...","calling":{"type":"freeCalling","webexCalling":{"phoneNumber":"...","extension":"...","locationId":"...","licenses":["..."]}},"calendar":{"type":"...","emailAddress":"...","resourceGroupId":"..."},"notes":"...","hotdeskingStatus":"on","deviceHostedMeetings":{"enabled":true,"siteUrl":"..."},"supportedDevices":"collaborationDevices","indoorNavigation":{"url":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show", short_help="Get Workspace Details.")
def show(
    workspace_id: str = typer.Argument(help="Webex PLACES id, from: wxcli workspaces list"),
    include_devices: str = typer.Option(None, "--include-devices", help="Flag identifying whether to include the devices associated with the workspace in the response."),
    include_capabilities: str = typer.Option(None, "--include-capabilities", help="Flag identifying whether to include the workspace capabilities in the response."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace Details.\n\n\b\nExample: wxcli workspaces show WORKSPACE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}"
    params = {}
    if include_devices is not None:
        params["includeDevices"] = include_devices
    if include_capabilities is not None:
        params["includeCapabilities"] = include_capabilities
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"displayName":"...","locationId":"...","workspaceLocationId":"...","floorId":"...","capacity":0,"type":"notSet","calendar":{"type":"...","emailAddress":"...","resourceGroupId":"..."},"sipAddress":"...","calling":{"type":"freeCalling","webexCalling":{"phoneNumber":"...","extension":"...","locationId":"...","licenses":["..."]}},"notes":"...","hotdeskingStatus":"on","deviceHostedMeetings":{"enabled":true,"siteUrl":"..."},"indoorNavigation":{"url":"..."}}'

@app.command("update", short_help="Update a Workspace.")
def update(
    workspace_id: str = typer.Argument(help="Webex PLACES id, from: wxcli workspaces list"),
    display_name: str = typer.Option(None, "--display-name", help="A friendly name for the workspace."),
    location_id: str = typer.Option(None, "--location-id", help="Location associated with the workspace. Must be provided when the `floorId` is set."),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="Legacy workspace location ID associated with the workspace. Prefer `locationId`."),
    floor_id: str = typer.Option(None, "--floor-id", help="Floor associated with the workspace."),
    capacity: str = typer.Option(None, "--capacity", help="How many people the workspace is suitable for. If set, must be 0 or higher."),
    type_param: str = typer.Option(None, "--type", help="Choices: notSet, focus, huddle, meetingRoom, open, desk, other"),
    sip_address: str = typer.Option(None, "--sip-address", help="The `sipAddress` field can only be provided when calling type is `thirdPartySipCalling`."),
    notes: str = typer.Option(None, "--notes", help="Notes associated to the workspace."),
    hotdesking_status: str = typer.Option(None, "--hotdesking-status", help="Choices: on, off"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Workspace.\n\n\b\nExample: wxcli workspaces update WORKSPACE_ID\n\n\b\nExample --json-body: '{"displayName":"...","locationId":"...","workspaceLocationId":"...","floorId":"...","capacity":0,"type":"notSet","calendar":{"type":"...","emailAddress":"...","resourceGroupId":"..."},"sipAddress":"...","calling":{"type":"freeCalling","webexCalling":{"phoneNumber":"...","extension":"...","locationId":"...","licenses":["..."]}},"notes":"...","hotdeskingStatus":"on","deviceHostedMeetings":{"enabled":true,"siteUrl":"..."},"indoorNavigation":{"url":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}"
    if json_body:
        body = load_json_body(json_body)
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": workspace_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Workspace.")
def delete(
    workspace_id: str = typer.Argument(help="Webex PLACES id, from: wxcli workspaces list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Workspace.\n\n\b\nExample: wxcli workspaces delete WORKSPACE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {workspace_id}?", abort=True)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {workspace_id}")
    else:
        emit({"status": "deleted", "id": workspace_id}, output=output, fields=fields)



@app.command("show-capabilities", short_help="Get Workspace Capabilities.")
def show_capabilities(
    workspace_id: str = typer.Argument(help="Webex PLACES id, from: wxcli workspaces list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace Capabilities.\n\n\b\nExample: wxcli workspaces show-capabilities WORKSPACE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaces/{workspace_id}/capabilities"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


