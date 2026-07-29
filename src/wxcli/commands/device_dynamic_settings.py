import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling device-dynamic-settings.")


@app.command("list", short_help="Read the List of Supported Devices.")
def cmd_list(
    allow_configure_layout_enabled: str = typer.Option(None, "--allow-configure-layout-enabled", help="List supported devices that allow the user to configure the layout."),
    type_param: str = typer.Option(None, "--type", help="List supported devices of a specific type. To excluded device types from a request or query, add `type=not:DEVICE_TYPE`. For example, `type=not:MPP`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("upgradeChannelList", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            if "max" not in params:
                params["max"] = 1000
            items = list(api.session.follow_pagination(url=url, params=params, item_key="upgradeChannelList"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Model', 'model'), ('Display Name', 'displayName'), ('Type', 'type')], limit=limit)



@app.command("list-settings-groups", short_help="Get Settings Groups.")
def list_settings_groups(
    family_or_model_display_name: str = typer.Option(None, "--family-or-model-display-name", help="Device family or model display name to filter the `settingsGroups`."),
    include_settings_type: str = typer.Option(None, "--include-settings-type", help="Choices: TABS, GROUPS, ALL"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("settingsGroups", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Friendly Name', 'friendlyName'), ('Path', 'path'), ('Tab', 'tab'), ('Family Or Model Display Name', 'familyOrModelDisplayName')], limit=limit)



_BODY_SKELETON_GET_CUSTOMER_DEVICE = '{"tags":["..."]}'

@app.command("get-customer-device", short_help="Get Customer Device Dynamic Settings.")
def get_customer_device(
    family_or_model_display_name: str = typer.Option(..., "--family-or-model-display-name", help="The family or model name for the device. If no tag is specified, all tags related to `familyOrModelDisplayName` are returned."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Customer Device Dynamic Settings.\n\n\b\nExample: wxcli device-dynamic-settings get-customer-device --family-or-model-display-name FAMILY_OR_MODEL_DISPLAY_NAME\n\n\b\nExample --json-body: '{"tags":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_GET_CUSTOMER_DEVICE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/devices/dynamicSettings/actions/getSettings/invoke"
    params = {}
    if family_or_model_display_name is not None:
        params["familyOrModelDisplayName"] = family_or_model_display_name
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_GET_LOCATION_DEVICE = '{"tags":["..."]}'

@app.command("get-location-device", short_help="Get Location Device Dynamic Settings.")
def get_location_device(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli locations list"),
    family_or_model_display_name: str = typer.Option(..., "--family-or-model-display-name", help="The family or model name for the device. If no tag is specified, all tags related to `familyOrModelDisplayName` are returned."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Device Dynamic Settings.\n\n\b\nExample: wxcli device-dynamic-settings get-location-device LOCATION_ID --family-or-model-display-name FAMILY_OR_MODEL_DISPLAY_NAME\n\n\b\nExample --json-body: '{"tags":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_GET_LOCATION_DEVICE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/locations/{location_id}/devices/dynamicSettings/actions/getSettings/invoke"
    params = {}
    if family_or_model_display_name is not None:
        params["familyOrModelDisplayName"] = family_or_model_display_name
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_GET_DEVICE_DYNAMIC = '{"tags":["..."]}'

@app.command("get-device-dynamic", short_help="Get Device Dynamic Settings.")
def get_device_dynamic(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Dynamic Settings.\n\n\b\nExample: wxcli device-dynamic-settings get-device-dynamic DEVICE_ID\n\n\b\nExample --json-body: '{"tags":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_GET_DEVICE_DYNAMIC), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/lists/devices/{device_id}/dynamicSettings/actions/getSettings/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"tags":[{"tag":"...","action":"ADD","value":"..."}]}'

@app.command("update", short_help="Update Device Dynamic Settings.")
def update(
    device_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli devices list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Dynamic Settings.\n\n\b\nExample: wxcli device-dynamic-settings update DEVICE_ID\n\n\b\nExample --json-body: '{"tags":[{"tag":"...","action":"ADD","value":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/devices/{device_id}/dynamicSettings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated", "id": device_id}, output=output, fields=fields)



@app.command("list-dynamic-device-settings", short_help="List Device Dynamic Settings Jobs.")
def list_dynamic_device_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Tracking ID', 'trackingId'), ('Source User ID', 'sourceUserId'), ('Source Customer ID', 'sourceCustomerId')], limit=limit)



_BODY_SKELETON_CREATE = '{"tags":[{"familyOrModelDisplayName":"...","tag":"...","action":"ADD","value":"..."}],"locationId":"..."}'

@app.command("create", short_help="Update Device Dynamic Settings Across Organization or Location.")
def create(
    location_id: str = typer.Option(None, "--location-id", help="If present, the requested settings will be updated to devices under this location."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Dynamic Settings Across Organization or Location.\n\n\b\nExample: wxcli device-dynamic-settings create --json-body '{"tags":[{"familyOrModelDisplayName":"...","tag":"...","action":"ADD"}]}'\n\n\b\nExample --json-body: '{"tags":[{"familyOrModelDisplayName":"...","tag":"...","action":"ADD","value":"..."}],"locationId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if location_id is not None:
            body["locationId"] = location_id
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



@app.command("show", short_help="Get Device Dynamic Settings Job Status.")
def show(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli device-dynamic-settings list-dynamic-device-settings"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Device Dynamic Settings Job Status.\n\n\b\nExample: wxcli device-dynamic-settings show JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/devices/dynamicDeviceSettings/{job_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-errors", short_help="List Device Dynamic Settings Job Errors.")
def list_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli device-dynamic-settings list-dynamic-device-settings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Device Dynamic Settings Job Errors.\n\n\b\nExample: wxcli device-dynamic-settings list-errors JOB_ID"""
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
    emit(items, output=output, fields=fields, columns=[('Tracking ID', 'trackingId'), ('Item', 'item'), ('Item Number', 'itemNumber')], limit=limit)


