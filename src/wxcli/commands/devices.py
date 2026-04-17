import json
import typer
from wxcli.errors import WebexError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling devices.")


@app.command("list")
def cmd_list(
    display_name: str = typer.Option(None, "--display-name", help="List devices with this display name."),
    person_id: str = typer.Option(None, "--person-id", help="List devices by person ID."),
    workspace_id: str = typer.Option(None, "--workspace-id", help="List devices by workspace ID."),
    connection_status: str = typer.Option(None, "--connection-status", help="List devices with this connection status."),
    product: str = typer.Option(None, "--product", help="Choices: DX-80, RoomKit, SX-80"),
    type_param: str = typer.Option(None, "--type", help="Choices: roomdesk, phone, accessory, webexgo, unknown"),
    serial: str = typer.Option(None, "--serial", help="List devices with this serial number."),
    tag: str = typer.Option(None, "--tag", help="List devices which have a tag. Searching for multiple tags"),
    software: str = typer.Option(None, "--software", help="List devices with this software version."),
    upgrade_channel: str = typer.Option(None, "--upgrade-channel", help="List devices with this upgrade channel."),
    error_code: str = typer.Option(None, "--error-code", help="List devices with this error code."),
    capability: str = typer.Option(None, "--capability", help="Choices: xapi"),
    permission: str = typer.Option(None, "--permission", help="List devices with this permission."),
    location_id: str = typer.Option(None, "--location-id", help="List devices by location ID."),
    workspace_location_id: str = typer.Option(None, "--workspace-location-id", help="List devices by workspace location ID. Deprecated, prefer `"),
    mac: str = typer.Option(None, "--mac", help="List devices with this MAC address."),
    device_platform: str = typer.Option(None, "--device-platform", help="Choices: cisco, microsoftTeamsRoom"),
    planned_maintenance: str = typer.Option(None, "--planned-maintenance", help="Choices: off, on, upcoming"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Devices."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices"
    params = {}
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
    except WebexError as e:
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
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Product', 'product'), ('MAC', 'mac')], limit=limit)



@app.command("create")
def create(
    mac: str = typer.Option(None, "--mac", help="(required) The MAC address of the device being created."),
    model: str = typer.Option(None, "--model", help="(required) The model of the device being created. The corresponding dev"),
    workspace_id: str = typer.Option(None, "--workspace-id", help="The ID of the workspace where the device will be created."),
    person_id: str = typer.Option(None, "--person-id", help="The ID of the person who will own the device once created."),
    password: str = typer.Option(None, "--password", help="SIP password to be configured for the phone, only required w"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Device by MAC Address."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        _missing = [f for f in ['mac', 'model'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
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
    device_id: str = typer.Argument(help="deviceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices/{device_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    device_id: str = typer.Argument(help="deviceId"),
    op: str = typer.Option(None, "--op", help="Choices: add, remove, replace"),
    path: str = typer.Option(None, "--path", help="Only the tags path is supported to patch."),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Device Tags\n\nExample --json-body:\n  '{"op":"add","path":"...","value":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices/{device_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        patch_op = {}
        if op is not None:
            patch_op["op"] = op
        if path is not None:
            patch_op["path"] = path
        if value is not None:
            try:
                patch_op["value"] = json.loads(value)
            except json.JSONDecodeError:
                patch_op["value"] = value
        body = [patch_op]
    try:
        result = api.session.rest_patch(url, json=body, params=params, content_type="application/json-patch+json")
    except WebexError as e:
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
    device_id: str = typer.Argument(help="deviceId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Device."""
    if not force:
        typer.confirm(f"Delete {device_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices/{device_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
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
    typer.echo(f"Deleted: {device_id}")



@app.command("create-activation-code")
def create_activation_code(
    workspace_id: str = typer.Option(None, "--workspace-id", help="The ID of the workspace where the device will be activated."),
    person_id: str = typer.Option(None, "--person-id", help="The ID of the person who will own the device once activated."),
    model: str = typer.Option(None, "--model", help="The model of the device being created. The corresponding dev"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Device Activation Code."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/devices/activationCode"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
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


