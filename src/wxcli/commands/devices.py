import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling devices.")


@app.command("list")
def cmd_list(
    max: str = typer.Option(None, "--max", help="Limit the maximum number of devices in the response."),
    start: str = typer.Option(None, "--start", help="Offset. Default is 0."),
    display_name: str = typer.Option(None, "--display-name", help="List devices with this display name."),
    person_id: str = typer.Option(None, "--person-id", help="List devices by person ID."),
    workspace_id: str = typer.Option(None, "--workspace-id", help="List devices by workspace ID."),
    connection_status: str = typer.Option(None, "--connection-status", help="List devices with this connection status."),
    product: str = typer.Option(None, "--product", help="List devices with this product name."),
    type_param: str = typer.Option(None, "--type", help="List devices with this type."),
    serial: str = typer.Option(None, "--serial", help="List devices with this serial number."),
    tag: str = typer.Option(None, "--tag", help="List devices which have a tag. Searching for multiple tags"),
    software: str = typer.Option(None, "--software", help="List devices with this software version."),
    upgrade_channel: str = typer.Option(None, "--upgrade-channel", help="List devices with this upgrade channel."),
    error_code: str = typer.Option(None, "--error-code", help="List devices with this error code."),
    capability: str = typer.Option(None, "--capability", help="List devices with this capability."),
    permission: str = typer.Option(None, "--permission", help="List devices with this permission."),
    location_id: str = typer.Option(None, "--location-id", help="List devices by location ID."),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="List devices by workspace location ID. Deprecated, prefer `"),
    mac: str = typer.Option(None, "--mac", help="List devices with this MAC address."),
    device_platform: str = typer.Option(None, "--device-platform", help="List devices with this device platform."),
    planned_maintenance: str = typer.Option(None, "--planned-maintenance", help="List devices with this planned maintenance."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Devices."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if display_name is not None:
        params["displayName"] = display_name
    if person_id is not None:
        params["personId"] = person_id
    if workspace_id is not None:
        params["workspaceId"] = workspace_id
    if connection_status is not None:
        params["connectionStatus"] = connection_status
    if product is not None:
        params["product"] = product
    if type_param is not None:
        params["type"] = type_param
    if serial is not None:
        params["serial"] = serial
    if tag is not None:
        params["tag"] = tag
    if software is not None:
        params["software"] = software
    if upgrade_channel is not None:
        params["upgradeChannel"] = upgrade_channel
    if error_code is not None:
        params["errorCode"] = error_code
    if capability is not None:
        params["capability"] = capability
    if permission is not None:
        params["permission"] = permission
    if location_id is not None:
        params["locationId"] = location_id
    if workspace_location_id is not None:
        params["workspaceLocationId"] = workspace_location_id
    if mac is not None:
        params["mac"] = mac
    if device_platform is not None:
        params["devicePlatform"] = device_platform
    if planned_maintenance is not None:
        params["plannedMaintenance"] = planned_maintenance
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
    items = result.get("devices", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    mac: str = typer.Option(None, "--mac", help=""),
    model: str = typer.Option(None, "--model", help=""),
    workspace_id: str = typer.Option(None, "--workspace-id", help=""),
    person_id: str = typer.Option(None, "--person-id", help=""),
    password: str = typer.Option(None, "--password", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Device by MAC Address."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if mac is not None:
            body["mac"] = mac
        if model is not None:
            body["model"] = model
        if workspace_id is not None:
            body["workspaceId"] = workspace_id
        if person_id is not None:
            body["personId"] = person_id
        if password is not None:
            body["password"] = password
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
    device_id: str = typer.Argument(help="deviceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices/{device_id}"
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



@app.command("delete")
def delete(
    device_id: str = typer.Argument(help="deviceId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Device."""
    if not force:
        typer.confirm(f"Delete {device_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices/{device_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {device_id}")



@app.command("update")
def update(
    device_id: str = typer.Argument(help="deviceId"),
    op: str = typer.Option(None, "--op", help=""),
    path: str = typer.Option(None, "--path", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Device Tags."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices/{device_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if op is not None:
            body["op"] = op
        if path is not None:
            body["path"] = path
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



@app.command("create-activation-code")
def create_activation_code(
    workspace_id: str = typer.Option(None, "--workspace-id", help=""),
    person_id: str = typer.Option(None, "--person-id", help=""),
    model: str = typer.Option(None, "--model", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Device Activation Code."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices/activationCode"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if workspace_id is not None:
            body["workspaceId"] = workspace_id
        if person_id is not None:
            body["personId"] = person_id
        if model is not None:
            body["model"] = model
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


