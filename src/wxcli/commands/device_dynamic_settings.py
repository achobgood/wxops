import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling device-dynamic-settings.")


@app.command("list")
def cmd_list(
    allow_configure_layout_enabled: str = typer.Option(None, "--allow-configure-layout-enabled", help="List supported devices that allow the user to configure the"),
    type_param: str = typer.Option(None, "--type", help="List supported devices of a specific type. To excluded devic"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
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
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("upgradeChannelList", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            if "max" not in params:
                params["max"] = 1000
            items = list(api.session.follow_pagination(url=url, params=params, item_key="upgradeChannelList"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Model', 'model'), ('Display Name', 'displayName'), ('Type', 'type')], limit=limit)



@app.command("list-settings-groups")
def list_settings_groups(
    family_or_model_display_name: str = typer.Option(None, "--family-or-model-display-name", help="Device family or model display name to filter the `settingsG"),
    include_settings_type: str = typer.Option(None, "--include-settings-type", help="Choices: TABS, GROUPS, ALL"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Settings Groups."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/dynamicSettings/settingsGroups"
    params = {}
    if family_or_model_display_name is not None:
        params["familyOrModelDisplayName"] = family_or_model_display_name
    if include_settings_type is not None:
        params["includeSettingsType"] = include_settings_type
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("settingsGroups", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("get-customer-device")
def get_customer_device(
    family_or_model_display_name: str = typer.Option(..., "--family-or-model-display-name", help="The family or model name for the device. If no tag is specif"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Customer Device Dynamic Settings\n\nExample --json-body:\n  '{"tags":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/devices/dynamicSettings/actions/getSettings/invoke"
    params = {}
    if family_or_model_display_name is not None:
        params["familyOrModelDisplayName"] = family_or_model_display_name
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    print_json(result)



@app.command("get-location-device")
def get_location_device(
    location_id: str = typer.Argument(help="locationId"),
    family_or_model_display_name: str = typer.Option(..., "--family-or-model-display-name", help="The family or model name for the device. If no tag is specif"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Device Dynamic Settings\n\nExample --json-body:\n  '{"tags":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/locations/{location_id}/devices/dynamicSettings/actions/getSettings/invoke"
    params = {}
    if family_or_model_display_name is not None:
        params["familyOrModelDisplayName"] = family_or_model_display_name
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    print_json(result)



@app.command("get-device-dynamic")
def get_device_dynamic(
    device_id: str = typer.Argument(help="deviceId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Dynamic Settings\n\nExample --json-body:\n  '{"tags":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/devices/{device_id}/dynamicSettings/actions/getSettings/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    print_json(result)



@app.command("update")
def update(
    device_id: str = typer.Argument(help="deviceId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Dynamic Settings\n\nExample --json-body:\n  '{"tags":[{"tag":"...","action":"...","value":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/dynamicSettings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-dynamic-device-settings")
def list_dynamic_device_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Device Dynamic Settings Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    location_id: str = typer.Option(None, "--location-id", help="If present, the requested settings will be updated to device"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Dynamic Settings Across Organization or Location\n\nExample --json-body:\n  '{"tags":[{"familyOrModelDisplayName":"...","tag":"...","action":"...","value":"..."}],"locationId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if location_id is not None:
            body["locationId"] = location_id
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
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
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Dynamic Settings Job Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings/{job_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("list-errors")
def list_errors(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Device Dynamic Settings Job Errors."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings/{job_id}/errors"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


