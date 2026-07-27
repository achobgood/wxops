import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling mode-management.")


@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Mode Management Features."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("features", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-common-modes")
def list_common_modes(
    feature_ids: str = typer.Option(..., "--feature-ids", help="List of feature IDs (comma-separated) for auto attendants, call queues, or hunt groups"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Common Modes."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/commonModes"
    params = {}
    if feature_ids is not None:
        params["featureIds"] = feature_ids
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("commonModeNames", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_SWITCH_MODE_FOR_INVOKE = '{"featureIds":["..."],"operatingModeName":"..."}'

@app.command("switch-mode-for-invoke")
def switch_mode_for_invoke(
    operating_mode_name: str = typer.Option(None, "--operating-mode-name", help="Name of the common operating mode to be set as current operating mode"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Multiple Features\n\nExample --json-body:\n  '{"featureIds":["..."],"operatingModeName":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_SWITCH_MODE_FOR_INVOKE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/actions/switchMode/invoke"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if operating_mode_name is not None:
            body["operatingModeName"] = operating_mode_name
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show")
def show(
    feature_id: str = typer.Argument(help="featureId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Mode Management Feature."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-normal-operation-mode")
def show_normal_operation_mode(
    feature_id: str = typer.Argument(help="featureId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Normal Operation Mode."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/normalOperationMode"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-modes")
def show_modes(
    feature_id: str = typer.Argument(help="featureId"),
    mode_id: str = typer.Argument(help="modeId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Operating Mode."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/modes/{mode_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("switch-to-normal")
def switch_to_normal(
    feature_id: str = typer.Argument(help="featureId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch to Normal Operation."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/actions/switchToNormalOperation/invoke"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_SWITCH_MODE_FOR_INVOKE_1 = '{"operatingModeId":"...","isManualSwitchbackEnabled":true}'

@app.command("switch-mode-for-invoke-1")
def switch_mode_for_invoke_1(
    feature_id: str = typer.Argument(help="featureId"),
    operating_mode_id: str = typer.Option(None, "--operating-mode-id", help="Operating mode ID to switch to"),
    is_manual_switchback_enabled: str = typer.Option(None, "--is-manual-switchback-enabled", help="Determines if switch back will be manual (if true) or automatic (if false or omitted from request)"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Single Feature\n\nExample --json-body:\n  '{"operatingModeId":"...","isManualSwitchbackEnabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_SWITCH_MODE_FOR_INVOKE_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/actions/switchMode/invoke"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if operating_mode_id is not None:
            body["operatingModeId"] = operating_mode_id
        if is_manual_switchback_enabled is not None:
            body["isManualSwitchbackEnabled"] = is_manual_switchback_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_EXTEND_CURRENT_OPERATING = '{"operatingModeId":"...","extensionTime":0}'

@app.command("extend-current-operating")
def extend_current_operating(
    feature_id: str = typer.Argument(help="featureId"),
    operating_mode_id: str = typer.Option(None, "--operating-mode-id", help="Unique identifier for the operating mode for which the extension is being configured."),
    extension_time: str = typer.Option(None, "--extension-time", help="Extension time in minutes (must be multiple of 30). If not sent, mode is extended with manual switch back exception"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Extend Current Operating Mode Duration\n\nExample --json-body:\n  '{"operatingModeId":"...","extensionTime":0}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_EXTEND_CURRENT_OPERATING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/actions/extendMode/invoke"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if operating_mode_id is not None:
            body["operatingModeId"] = operating_mode_id
        if extension_time is not None:
            body["extensionTime"] = extension_time
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


