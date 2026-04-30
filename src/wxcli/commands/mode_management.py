import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling mode-management.")


@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("features", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-common-modes")
def list_common_modes(
    feature_ids: str = typer.Option(..., "--feature-ids", help="List of feature IDs (comma-separated) for auto attendants, c"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("commonModeNames", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("switch-mode-for-invoke")
def switch_mode_for_invoke(
    operating_mode_name: str = typer.Option(None, "--operating-mode-name", help="Name of the common operating mode to be set as current opera"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Multiple Features\n\nExample --json-body:\n  '{"featureIds":["..."],"operatingModeName":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/actions/switchMode/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if operating_mode_name is not None:
            body["operatingModeName"] = operating_mode_name
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    print_json(result)



@app.command("show")
def show(
    feature_id: str = typer.Argument(help="featureId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Mode Management Feature."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}"
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



@app.command("show-normal-operation-mode")
def show_normal_operation_mode(
    feature_id: str = typer.Argument(help="featureId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Normal Operation Mode."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/normalOperationMode"
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



@app.command("show-modes")
def show_modes(
    feature_id: str = typer.Argument(help="featureId"),
    mode_id: str = typer.Argument(help="modeId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Operating Mode."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/modes/{mode_id}"
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



@app.command("switch-to-normal")
def switch_to_normal(
    feature_id: str = typer.Argument(help="featureId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch to Normal Operation."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/actions/switchToNormalOperation/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    print_json(result)



@app.command("switch-mode-for-invoke-1")
def switch_mode_for_invoke_1(
    feature_id: str = typer.Argument(help="featureId"),
    operating_mode_id: str = typer.Option(None, "--operating-mode-id", help="Operating mode ID to switch to"),
    is_manual_switchback_enabled: str = typer.Option(None, "--is-manual-switchback-enabled", help="Determines if switch back will be manual (if true) or automa"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Single Feature."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/actions/switchMode/invoke"
    if json_body:
        body = json.loads(json_body)
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
    print_json(result)



@app.command("extend-current-operating")
def extend_current_operating(
    feature_id: str = typer.Argument(help="featureId"),
    operating_mode_id: str = typer.Option(None, "--operating-mode-id", help="Unique identifier for the operating mode for which the exten"),
    extension_time: str = typer.Option(None, "--extension-time", help="Extension time in minutes (must be multiple of 30). If not s"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Extend Current Operating Mode Duration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{feature_id}/actions/extendMode/invoke"
    if json_body:
        body = json.loads(json_body)
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
    print_json(result)


