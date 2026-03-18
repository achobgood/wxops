import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling device-call-settings-with-device-dynamic-settings.")


@app.command("list")
def cmd_list(
    allow_configure_layout_enabled: str = typer.Option(None, "--allow-configure-layout-enabled", help="List supported devices that allow the user to configure the"),
    type_param: str = typer.Option(None, "--type", help="List supported devices of a specific type. To excluded devic"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Supported Devices."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supportedDevices"
    params = {}
    if allow_configure_layout_enabled is not None:
        params["allowConfigureLayoutEnabled"] = allow_configure_layout_enabled
    if type_param is not None:
        params["type"] = type_param
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
        print_table(items, columns=[('Model', 'model'), ('Display Name', 'displayName'), ('Type', 'type')], limit=limit)



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Settings Groups."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/dynamicSettings/settingsGroups"
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



@app.command("get-customer-device")
def get_customer_device(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Customer Device Dynamic Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/devices/dynamicSettings/actions/getSettings/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("get-location-device")
def get_location_device(
    location_id: str = typer.Argument(help="locationId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Device Dynamic Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/locations/{location_id}/devices/dynamicSettings/actions/getSettings/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("get-device-dynamic")
def get_device_dynamic(
    device_id: str = typer.Argument(help="deviceId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Dynamic Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/devices/{device_id}/dynamicSettings/actions/getSettings/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
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
    device_id: str = typer.Argument(help="deviceId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Dynamic Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/dynamicSettings"
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



@app.command("create")
def create(
    location_id: str = typer.Option(None, "--location-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Dynamic Settings Across Organization or Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if location_id is not None:
            body["locationId"] = location_id
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



@app.command("show-dynamic-device-settings-devices")
def show_dynamic_device_settings_devices(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Device Dynamic Settings Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings"
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



@app.command("show-dynamic-device-settings-devices-1")
def show_dynamic_device_settings_devices_1(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Dynamic Settings Job Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings/{job_id}"
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



@app.command("show-errors")
def show_errors(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Device Dynamic Settings Job Errors."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings/{job_id}/errors"
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


