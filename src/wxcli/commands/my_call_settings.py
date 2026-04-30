import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling my-call-settings.")


@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List Available Preferred Answer Endpoints."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/availablePreferredAnswerEndpoints"
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
    items = result.get("endpoints", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-preferred-answer-endpoints")
def list_available_preferred_answer_endpoints(
    line_owner_id: str = typer.Argument(help="lineOwnerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Available Preferred Answer Endpoint List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{line_owner_id}/availablePreferredAnswerEndpoints"
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
    items = result.get("endpoints", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/preferredAnswerEndpoint"
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



@app.command("update")
def update(
    preferred_answer_endpoint_id: str = typer.Option(None, "--preferred-answer-endpoint-id", help="Person’s preferred answer endpoint."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/preferredAnswerEndpoint"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if preferred_answer_endpoint_id is not None:
            body["preferredAnswerEndpointId"] = preferred_answer_endpoint_id
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-preferred-answer-endpoint")
def show_preferred_answer_endpoint(
    line_owner_id: str = typer.Argument(help="lineOwnerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{line_owner_id}/preferredAnswerEndpoint"
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



@app.command("update-preferred-answer-endpoint")
def update_preferred_answer_endpoint(
    line_owner_id: str = typer.Argument(help="lineOwnerId"),
    preferred_answer_endpoint_id: str = typer.Option(None, "--preferred-answer-endpoint-id", help="Person’s preferred answer endpoint."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{line_owner_id}/preferredAnswerEndpoint"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if preferred_answer_endpoint_id is not None:
            body["preferredAnswerEndpointId"] = preferred_answer_endpoint_id
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-webex-go-override")
def show_webex_go_override(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My WebexGoOverride Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/webexGoOverride"
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



@app.command("update-webex-go-override")
def update_webex_go_override(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="True if the \"Mobile User Aware\" override setting for Do Not"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My WebexGoOverride Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/webexGoOverride"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-caller-id-settings")
def show_caller_id_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callerId"
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



@app.command("update-caller-id-settings")
def update_caller_id_settings(
    calling_line_id_delivery_blocking_enabled: bool = typer.Option(None, "--calling-line-id-delivery-blocking-enabled/--no-calling-line-id-delivery-blocking-enabled", help="If `true`, the user's name and phone number are not shown to"),
    connected_line_identification_restriction_enabled: bool = typer.Option(None, "--connected-line-identification-restriction-enabled/--no-connected-line-identification-restriction-enabled", help="If `true`, the user's name and phone number are not shown wh"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callerId"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if calling_line_id_delivery_blocking_enabled is not None:
            body["callingLineIdDeliveryBlockingEnabled"] = calling_line_id_delivery_blocking_enabled
        if connected_line_identification_restriction_enabled is not None:
            body["connectedLineIdentificationRestrictionEnabled"] = connected_line_identification_restriction_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-caller-id-secondary-lines")
def show_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callerId"
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



@app.command("update-caller-id-secondary-lines")
def update_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    calling_line_id_delivery_blocking_enabled: bool = typer.Option(None, "--calling-line-id-delivery-blocking-enabled/--no-calling-line-id-delivery-blocking-enabled", help="If `true`, the user's name and phone number are not shown to"),
    connected_line_identification_restriction_enabled: bool = typer.Option(None, "--connected-line-identification-restriction-enabled/--no-connected-line-identification-restriction-enabled", help="If `true`, the user's name and phone number are not shown wh"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callerId"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if calling_line_id_delivery_blocking_enabled is not None:
            body["callingLineIdDeliveryBlockingEnabled"] = calling_line_id_delivery_blocking_enabled
        if connected_line_identification_restriction_enabled is not None:
            body["connectedLineIdentificationRestrictionEnabled"] = connected_line_identification_restriction_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-selected-caller-id-settings")
def show_selected_caller_id_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read My Selected Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectedCallerId"
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



@app.command("update-selected-caller-id-settings")
def update_selected_caller_id_settings(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure My Selected Caller ID Settings\n\nExample --json-body:\n  '{"selected":{"type":"DEFAULT_CLID","id":"...","directNumber":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectedCallerId"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-selected-caller-id-secondary-lines")
def show_selected_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Selected Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/selectedCallerId"
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



@app.command("update-selected-caller-id-secondary-lines")
def update_selected_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Selected Caller ID Settings\n\nExample --json-body:\n  '{"selected":{"type":"DEFAULT_CLID","id":"...","directNumber":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/selectedCallerId"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-available-caller-ids-settings")
def list_available_caller_ids_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Available Caller ID List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/availableCallerIds"
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
    items = result.get("availableCallerIds", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-caller-ids-secondary-lines")
def list_available_caller_ids_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Available Caller ID List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/availableCallerIds"
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
    items = result.get("availableCallerIds", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-endpoints")
def list_endpoints(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of My Endpoints."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/endpoints"
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
    items = result.get("endpoints", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-endpoints")
def show_endpoints(
    endpoint_id: str = typer.Argument(help="endpointId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Endpoints Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/endpoints/{endpoint_id}"
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



@app.command("update-endpoints")
def update_endpoints(
    endpoint_id: str = typer.Argument(help="endpointId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Endpoints Details\n\nExample --json-body:\n  '{"mobilitySettings":{"alertingEnabled":true}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/endpoints/{endpoint_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-call-recording-settings")
def show_call_recording_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Recording Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callRecording"
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



@app.command("show-call-recording-secondary-lines")
def show_call_recording_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Call Recording Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callRecording"
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



@app.command("show-me")
def show_me(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Own Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me"
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



@app.command("list-feature-access-code-settings")
def list_feature_access_code_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Feature Access Codes."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/featureAccessCode"
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
    items = result.get("featureAccessCodeList", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-feature-access-code-secondary-lines")
def list_feature_access_code_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Feature Access Codes For Secondary Line Owner."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/featureAccessCode"
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
    items = result.get("featureAccessCodeList", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-assigned-assistants")
def list_assigned_assistants(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Executive Assigned Assistants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/executive/assignedAssistants"
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
    items = result.get("assistants", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-assigned-assistants")
def update_assigned_assistants(
    allow_opt_in_out_enabled: bool = typer.Option(None, "--allow-opt-in-out-enabled/--no-allow-opt-in-out-enabled", help="If `true`, the executive can allow assistants to opt in or o"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Executive Assigned Assistants\n\nExample --json-body:\n  '{"allowOptInOutEnabled":true,"assistantIds":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/executive/assignedAssistants"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if allow_opt_in_out_enabled is not None:
            body["allowOptInOutEnabled"] = allow_opt_in_out_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-available-assistants")
def list_available_assistants(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Executive Available Assistants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/executive/availableAssistants"
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
    items = result.get("assistants", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-assistant")
def list_assistant(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Executive Assistant Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/executive/assistant"
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
    items = result.get("executives", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-assistant")
def update_assistant(
    forward_filtered_calls_enabled: bool = typer.Option(None, "--forward-filtered-calls-enabled/--no-forward-filtered-calls-enabled", help="If `true`, filtered calls to assistant are forwarded to the"),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="Phone number to forward the filtered calls to. Mandatory if"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Executive Assistant Settings\n\nExample --json-body:\n  '{"forwardFilteredCallsEnabled":true,"forwardToPhoneNumber":"...","executives":[{"personId":"...","optInEnabled":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/executive/assistant"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if forward_filtered_calls_enabled is not None:
            body["forwardFilteredCallsEnabled"] = forward_filtered_calls_enabled
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-services-settings")
def list_services_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Calling Services List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/services"
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
    items = result.get("services", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-services-secondary-lines")
def list_services_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Calling Services List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/services"
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
    items = result.get("services", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-single-number-reach")
def list_single_number_reach(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User's Single Number Reach Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach"
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
    items = result.get("numbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-single-number-reach")
def update_single_number_reach(
    alert_all_locations_for_click_to_dial_calls_enabled: bool = typer.Option(None, "--alert-all-locations-for-click-to-dial-calls-enabled/--no-alert-all-locations-for-click-to-dial-calls-enabled", help="If `true`, all locations will be alerted for click-to-dial c"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify User's Single Number Reach Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if alert_all_locations_for_click_to_dial_calls_enabled is not None:
            body["alertAllLocationsForClickToDialCallsEnabled"] = alert_all_locations_for_click_to_dial_calls_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create")
def create(
    phone_number: str = typer.Option(None, "--phone-number", help="(required) Phone number."),
    name: str = typer.Option(None, "--name", help="(required) Name associated with the phone number."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="(required) If `true`, the phone number is enabled."),
    do_not_forward_calls_enabled: bool = typer.Option(None, "--do-not-forward-calls-enabled/--no-do-not-forward-calls-enabled", help="Note that this setting attempts to prevent the Single Number"),
    answer_confirmation_enabled: bool = typer.Option(None, "--answer-confirmation-enabled/--no-answer-confirmation-enabled", help="If `true`, answer confirmation is enabled. The default value"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add phone number as User's Single Number Reach."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach/numbers"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if name is not None:
            body["name"] = name
        if enabled is not None:
            body["enabled"] = enabled
        if do_not_forward_calls_enabled is not None:
            body["doNotForwardCallsEnabled"] = do_not_forward_calls_enabled
        if answer_confirmation_enabled is not None:
            body["answerConfirmationEnabled"] = answer_confirmation_enabled
        _missing = [f for f in ['phoneNumber', 'name', 'enabled'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("update-numbers")
def update_numbers(
    phone_number_id: str = typer.Argument(help="phoneNumberId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number."),
    name: str = typer.Option(None, "--name", help="Name associated with the phone number."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="If `true`, the phone number is enabled."),
    do_not_forward_calls_enabled: bool = typer.Option(None, "--do-not-forward-calls-enabled/--no-do-not-forward-calls-enabled", help="If `true`, calls are not forwarded."),
    answer_confirmation_enabled: bool = typer.Option(None, "--answer-confirmation-enabled/--no-answer-confirmation-enabled", help="If `true`, answer confirmation is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify User's Single Number Reach Contact Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach/numbers/{phone_number_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if name is not None:
            body["name"] = name
        if enabled is not None:
            body["enabled"] = enabled
        if do_not_forward_calls_enabled is not None:
            body["doNotForwardCallsEnabled"] = do_not_forward_calls_enabled
        if answer_confirmation_enabled is not None:
            body["answerConfirmationEnabled"] = answer_confirmation_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    phone_number_id: str = typer.Argument(help="phoneNumberId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete User's Single Number Reach Contact Settings."""
    if not force:
        typer.confirm(f"Delete {phone_number_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach/numbers/{phone_number_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {phone_number_id}")



@app.command("show-call-forwarding-settings")
def show_call_forwarding_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read My Call Forwarding Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callForwarding"
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



@app.command("update-call-forwarding-settings")
def update_call_forwarding_settings(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure My Call Forwarding Settings\n\nExample --json-body:\n  '{"callForwarding":{"always":{"enabled":"...","destination":"...","ringReminderEnabled":"...","destinationVoicemailEnabled":"..."},"busy":{"enabled":"...","destination":"...","destinationVoicemailEnabled":"..."},"noAnswer":{"enabled":"...","destination":"...","numberOfRings":"...","destinationVoicemailEnabled":"..."}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callForwarding"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-call-forwarding-secondary-lines")
def show_call_forwarding_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Call Forwarding Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callForwarding"
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



@app.command("update-call-forwarding-secondary-lines")
def update_call_forwarding_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Call Forwarding Settings\n\nExample --json-body:\n  '{"callForwarding":{"always":{"enabled":"...","destination":"...","ringReminderEnabled":"...","destinationVoicemailEnabled":"..."},"busy":{"enabled":"...","destination":"...","destinationVoicemailEnabled":"..."},"noAnswer":{"enabled":"...","destination":"...","numberOfRings":"...","destinationVoicemailEnabled":"..."}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callForwarding"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-call-pickup-group-settings")
def list_call_pickup_group_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Pickup Group Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callPickupGroup"
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
    items = result.get("memberList", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-call-pickup-group-secondary-lines")
def list_call_pickup_group_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Call Pickup Group Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callPickupGroup"
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
    items = result.get("memberList", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-call-park-settings")
def list_call_park_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Park Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callPark"
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
    items = result.get("memberList", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-call-park-secondary-lines")
def list_call_park_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Call Park Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callPark"
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
    items = result.get("memberList", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-voicemail-settings")
def show_voicemail_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Voicemail Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/voicemail"
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



@app.command("update-voicemail-settings")
def update_voicemail_settings(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Voicemail is enabled or disabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Voicemail Settings for a Person\n\nExample --json-body:\n  '{"notifications":{"enabled":true,"destination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/voicemail"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-voicemail-secondary-lines")
def show_voicemail_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Voicemail Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/voicemail"
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



@app.command("update-voicemail-secondary-lines")
def update_voicemail_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Voicemail is enabled or disabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Voicemail Settings\n\nExample --json-body:\n  '{"notifications":{"enabled":true,"destination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/voicemail"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-call-block")
def list_call_block(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Block Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callBlock"
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
    items = result.get("numbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-numbers")
def create_numbers(
    phone_number: str = typer.Option(None, "--phone-number", help="(required) Phone number which is blocked by user."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a phone number to user's Call Block List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callBlock/numbers"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        _missing = [f for f in ['phoneNumber'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-numbers")
def show_numbers(
    phone_number_id: str = typer.Argument(help="phoneNumberId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Block State For Specific Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callBlock/numbers/{phone_number_id}"
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



@app.command("delete-numbers")
def delete_numbers(
    phone_number_id: str = typer.Argument(help="phoneNumberId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete User Call Block Number."""
    if not force:
        typer.confirm(f"Delete {phone_number_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callBlock/numbers/{phone_number_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {phone_number_id}")



@app.command("list-monitoring")
def list_monitoring(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Monitoring Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/monitoring"
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
    items = result.get("monitoredElements", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-queues-settings")
def list_queues_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Center Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/queues"
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
    items = result.get("queues", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-queues-settings")
def update_queues_settings(
    agent_acd_state: str = typer.Option(None, "--agent-acd-state", help="Choices: SIGN_IN, SIGN_OUT, AVAILABLE, UNAVAILABLE, WRAP_UP"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Call Center Settings\n\nExample --json-body:\n  '{"agentACDState":"SIGN_IN","queues":[{"id":"...","available":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/queues"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_acd_state is not None:
            body["agentACDState"] = agent_acd_state
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-queues-secondary-lines")
def list_queues_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Call Center Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/queues"
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
    items = result.get("queues", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-queues-secondary-lines")
def update_queues_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    agent_acd_state: str = typer.Option(None, "--agent-acd-state", help="Choices: SIGN_IN, SIGN_OUT, AVAILABLE, UNAVAILABLE, WRAP_UP"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Call Center Settings\n\nExample --json-body:\n  '{"agentACDState":"SIGN_IN","queues":[{"id":"...","available":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/queues"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_acd_state is not None:
            body["agentACDState"] = agent_acd_state
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-call-captions")
def show_call_captions(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get my call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callCaptions"
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



@app.command("list-priority-alert")
def list_priority_alert(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Priority Alert Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert"
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
    items = result.get("criteria", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-priority-alert")
def update_priority_alert(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Priority Alert feature is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Priority Alert Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-criteria-priority-alert")
def create_criteria_priority_alert(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this cri"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this c"),
    notification_enabled: bool = typer.Option(None, "--notification-enabled/--no-notification-enabled", help="Determines whether priority alerting is applied for calls ma"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a Priority Alert Criteria\n\nExample --json-body:\n  '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if notification_enabled is not None:
            body["notificationEnabled"] = notification_enabled
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-criteria-priority-alert")
def show_criteria_priority_alert(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Priority Alert Criteria Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert/criteria/{id}"
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



@app.command("update-criteria-priority-alert")
def update_criteria_priority_alert(
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this cri"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this c"),
    notification_enabled: bool = typer.Option(None, "--notification-enabled/--no-notification-enabled", help="Determines whether priority alerting is applied for calls ma"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Settings for a Priority Alert Criteria\n\nExample --json-body:\n  '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if notification_enabled is not None:
            body["notificationEnabled"] = notification_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-criteria-priority-alert")
def delete_criteria_priority_alert(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Priority Alert Criteria."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("list-schedules")
def list_schedules(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User (and Location) Schedules."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules"
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
    items = result.get("schedules", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-schedules")
def create_schedules(
    type_param: str = typer.Option(None, "--type", help="(required) Choices: businessHours, holidays"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the schedule."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a User level Schedule for Call Settings\n\nExample --json-body:\n  '{"type":"businessHours","name":"...","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":"...","recurrence":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
        if name is not None:
            body["name"] = name
        _missing = [f for f in ['type', 'name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-schedules-me")
def show_schedules_me(
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}"
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



@app.command("update-schedules")
def update_schedules(
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    name: str = typer.Option(None, "--name", help="Name of the schedule."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify User Schedule\n\nExample --json-body:\n  '{"name":"...","events":[{"name":"...","startDate":"...","endDate":"...","allDayEnabled":"...","newName":"...","startTime":"...","endTime":"...","recurrence":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-schedules")
def delete_schedules(
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a User Schedule."""
    if not force:
        typer.confirm(f"Delete {schedule_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {schedule_id}")



@app.command("create-events")
def create_events(
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    name: str = typer.Option(None, "--name", help="(required) Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="(required) Start Date of Event."),
    end_date: str = typer.Option(None, "--end-date", help="(required) End Date of Event."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of event."),
    end_time: str = typer.Option(None, "--end-time", help="End time of event."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="(required) An indication of whether given event is an all-day event or"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add an event for a User Schedule\n\nExample --json-body:\n  '{"name":"...","startDate":"...","endDate":"...","allDayEnabled":true,"startTime":"...","endTime":"...","recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":"..."},"recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."}}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}/events"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if all_day_enabled is not None:
            body["allDayEnabled"] = all_day_enabled
        _missing = [f for f in ['name', 'startDate', 'endDate', 'allDayEnabled'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-events")
def show_events(
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User Schedule Event."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
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



@app.command("update-events")
def update_events(
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    name: str = typer.Option(None, "--name", help="Name for the event."),
    new_name: str = typer.Option(None, "--new-name", help="New Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="Start Date of Event."),
    end_date: str = typer.Option(None, "--end-date", help="End Date of Event."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of event."),
    end_time: str = typer.Option(None, "--end-time", help="End time of event."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="An indication of whether given event is an all-day event or"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify User Schedule Event\n\nExample --json-body:\n  '{"name":"...","startDate":"...","endDate":"...","allDayEnabled":true,"newName":"...","startTime":"...","endTime":"...","recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":"..."},"recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."}}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if new_name is not None:
            body["newName"] = new_name
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if all_day_enabled is not None:
            body["allDayEnabled"] = all_day_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-events")
def delete_events(
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    event_id: str = typer.Argument(help="eventId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete User a Schedule Event."""
    if not force:
        typer.confirm(f"Delete {event_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {event_id}")



@app.command("show-schedules-locations")
def show_schedules_locations(
    schedule_type: str = typer.Argument(help="scheduleType"),
    schedule_id: str = typer.Argument(help="scheduleId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User's Location Level Schedule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/locations/schedules/{schedule_type}/{schedule_id}"
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



@app.command("list-call-notify")
def list_call_notify(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Notify Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify"
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
    items = result.get("criteria", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-call-notify")
def update_call_notify(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Indicates whether the call notify feature should be enabled"),
    email_address: str = typer.Option(None, "--email-address", help="Email Address to which call notifications to be received."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Call Notify Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if email_address is not None:
            body["emailAddress"] = email_address
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-criteria-call-notify")
def create_criteria_call_notify(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this cri"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this c"),
    notification_enabled: bool = typer.Option(None, "--notification-enabled/--no-notification-enabled", help="Determines whether call notification is applied for calls ma"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a Call Notify Criteria\n\nExample --json-body:\n  '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if notification_enabled is not None:
            body["notificationEnabled"] = notification_enabled
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-criteria-call-notify")
def show_criteria_call_notify(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Notify Criteria Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify/criteria/{id}"
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



@app.command("update-criteria-call-notify")
def update_criteria_call_notify(
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this cri"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this c"),
    notification_enabled: bool = typer.Option(None, "--notification-enabled/--no-notification-enabled", help="Determines whether call notification is applied for calls ma"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Call Notify Criteria\n\nExample --json-body:\n  '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if notification_enabled is not None:
            body["notificationEnabled"] = notification_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-criteria-call-notify")
def delete_criteria_call_notify(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Notify Criteria."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("list-selective-accept")
def list_selective_accept(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Accept Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept"
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
    items = result.get("criteria", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-selective-accept")
def update_selective_accept(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="indicates whether selective accept is enabled or not."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Selective Call Accept Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-criteria-selective-accept")
def create_criteria_selective_accept(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    accept_enabled: bool = typer.Option(None, "--accept-enabled/--no-accept-enabled", help="(required) Boolean flag indicating if selective call accept is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add User Selective Call Accept Criteria\n\nExample --json-body:\n  '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if accept_enabled is not None:
            body["acceptEnabled"] = accept_enabled
        _missing = [f for f in ['callsFrom', 'acceptEnabled'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-criteria-selective-accept")
def show_criteria_selective_accept(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Accept Criteria Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept/criteria/{id}"
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



@app.command("update-criteria-selective-accept")
def update_criteria_selective_accept(
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    accept_enabled: bool = typer.Option(None, "--accept-enabled/--no-accept-enabled", help="Boolean flag to enable/disable the selective accept criteria"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Selective Call Accept Criteria\n\nExample --json-body:\n  '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if accept_enabled is not None:
            body["acceptEnabled"] = accept_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-criteria-selective-accept")
def delete_criteria_selective_accept(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Accept Criteria."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("list-assigned-numbers")
def list_assigned_numbers(
    name: str = typer.Option(None, "--name", help="List numbers whose owner name contains this string."),
    phone_number: str = typer.Option(None, "--phone-number", help="List numbers whose phoneNumber contains this string."),
    extension: str = typer.Option(None, "--extension", help="List numbers whose extension contains this string."),
    order: str = typer.Option(None, "--order", help="Sort the list of numbers based on `lastName`, `dn`, `extensi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Numbers for User's Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/location/assignedNumbers"
    params = {}
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if extension is not None:
        params["extension"] = extension
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-criteria-selective-forward")
def create_criteria_selective_forward(
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="The phone number to which calls are forwarded when the crite"),
    destination_voicemail_enabled: bool = typer.Option(None, "--destination-voicemail-enabled/--no-destination-voicemail-enabled", help="Indicates whether calls that meet the criteria are forwarded"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this cri"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this c"),
    forward_enabled: bool = typer.Option(None, "--forward-enabled/--no-forward-enabled", help="Determines whether selective call forwarding is applied for"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a Selective Call Forwarding Criteria\n\nExample --json-body:\n  '{"forwardToPhoneNumber":"...","destinationVoicemailEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
        if destination_voicemail_enabled is not None:
            body["destinationVoicemailEnabled"] = destination_voicemail_enabled
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if forward_enabled is not None:
            body["forwardEnabled"] = forward_enabled
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-criteria-selective-forward")
def show_criteria_selective_forward(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Settings for a Selective Call Forwarding Criteria."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward/criteria/{id}"
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



@app.command("update-criteria-selective-forward")
def update_criteria_selective_forward(
    id: str = typer.Argument(help="id"),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="The phone number to which calls are forwarded when the crite"),
    destination_voicemail_enabled: bool = typer.Option(None, "--destination-voicemail-enabled/--no-destination-voicemail-enabled", help="Indicates whether calls that meet the criteria are forwarded"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this cri"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this c"),
    forward_enabled: bool = typer.Option(None, "--forward-enabled/--no-forward-enabled", help="Determines whether selective call forwarding is applied for"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Settings for a Selective Call Forwarding Criteria\n\nExample --json-body:\n  '{"forwardToPhoneNumber":"...","destinationVoicemailEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if forward_to_phone_number is not None:
            body["forwardToPhoneNumber"] = forward_to_phone_number
        if destination_voicemail_enabled is not None:
            body["destinationVoicemailEnabled"] = destination_voicemail_enabled
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if forward_enabled is not None:
            body["forwardEnabled"] = forward_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-criteria-selective-forward")
def delete_criteria_selective_forward(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Forwarding Criteria."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("list-selective-forward")
def list_selective_forward(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Forward Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward"
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
    items = result.get("criteria", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-selective-forward")
def update_selective_forward(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Selective Forward feature is enabled."),
    default_phone_number_to_forward: str = typer.Option(None, "--default-phone-number-to-forward", help="Enter the phone number to forward calls to during this sched"),
    ring_reminder_enabled: bool = typer.Option(None, "--ring-reminder-enabled/--no-ring-reminder-enabled", help="When `true`, enables a ring reminder for such calls."),
    destination_voicemail_enabled: bool = typer.Option(None, "--destination-voicemail-enabled/--no-destination-voicemail-enabled", help="Enables forwarding for all calls to voicemail. This option i"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Selective Call Forward Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if default_phone_number_to_forward is not None:
            body["defaultPhoneNumberToForward"] = default_phone_number_to_forward
        if ring_reminder_enabled is not None:
            body["ringReminderEnabled"] = ring_reminder_enabled
        if destination_voicemail_enabled is not None:
            body["destinationVoicemailEnabled"] = destination_voicemail_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-selective-reject")
def list_selective_reject(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Reject Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject"
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
    items = result.get("criteria", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-selective-reject")
def update_selective_reject(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="if `true`, selective reject is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Selective Call Reject Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-criteria-selective-reject")
def create_criteria_selective_reject(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, FORWARDED"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    reject_enabled: bool = typer.Option(None, "--reject-enabled/--no-reject-enabled", help="(required) Boolean flag to enable/disable rejection."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add User Selective Call Reject Criteria\n\nExample --json-body:\n  '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if reject_enabled is not None:
            body["rejectEnabled"] = reject_enabled
        _missing = [f for f in ['callsFrom', 'rejectEnabled'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-anonymous-call-reject")
def show_anonymous_call_reject(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Anonymous Call Rejection Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/anonymousCallReject"
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



@app.command("update-anonymous-call-reject")
def update_anonymous_call_reject(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Indicates whether Anonymous Call Rejection is enabled or not"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Anonymous Call Rejection Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/anonymousCallReject"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-criteria-selective-reject")
def show_criteria_selective_reject(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Reject Criteria Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject/criteria/{id}"
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



@app.command("update-criteria-selective-reject")
def update_criteria_selective_reject(
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, FORWARDED"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, privat"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavai"),
    reject_enabled: bool = typer.Option(None, "--reject-enabled/--no-reject-enabled", help="Boolean flag to enable/disable rejection."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Selective Call Reject Criteria\n\nExample --json-body:\n  '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if reject_enabled is not None:
            body["rejectEnabled"] = reject_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-criteria-selective-reject")
def delete_criteria_selective_reject(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Reject Criteria."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("show-call-waiting")
def show_call_waiting(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Waiting Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callWaiting"
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



@app.command("update-call-waiting")
def update_call_waiting(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable or disable Call Waiting for the user."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Call Waiting Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callWaiting"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-sequential-ring")
def list_sequential_ring(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Sequential Ring Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing"
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
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-sequential-ring")
def update_sequential_ring(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable or disable sequential ring for the user."),
    ring_base_location_first_enabled: bool = typer.Option(None, "--ring-base-location-first-enabled/--no-ring-base-location-first-enabled", help="When `true`, the user's own devices ring before sequential r"),
    base_location_number_of_rings: str = typer.Option(None, "--base-location-number-of-rings", help="Number of rings for the user's own devices. Minimum: 2, Maxi"),
    continue_if_base_location_is_busy_enabled: bool = typer.Option(None, "--continue-if-base-location-is-busy-enabled/--no-continue-if-base-location-is-busy-enabled", help="When `true`, sequential ring continues even when the user is"),
    calls_to_voicemail_enabled: bool = typer.Option(None, "--calls-to-voicemail-enabled/--no-calls-to-voicemail-enabled", help="When `true`, the caller is provided the option to press the"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Sequential Ring Settings for User\n\nExample --json-body:\n  '{"enabled":true,"ringBaseLocationFirstEnabled":true,"baseLocationNumberOfRings":0,"continueIfBaseLocationIsBusyEnabled":true,"callsToVoicemailEnabled":true,"phoneNumbers":[{"answerConfirmationRequiredEnabled":"...","numberOfRings":"...","phoneNumber":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if ring_base_location_first_enabled is not None:
            body["ringBaseLocationFirstEnabled"] = ring_base_location_first_enabled
        if base_location_number_of_rings is not None:
            body["baseLocationNumberOfRings"] = base_location_number_of_rings
        if continue_if_base_location_is_busy_enabled is not None:
            body["continueIfBaseLocationIsBusyEnabled"] = continue_if_base_location_is_busy_enabled
        if calls_to_voicemail_enabled is not None:
            body["callsToVoicemailEnabled"] = calls_to_voicemail_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-criteria-sequential-ring")
def create_criteria_sequential_ring(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the location's schedule which determines when the se"),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: holidays, businessHours"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: SELECT_PHONE_NUMBERS, ANY_PHONE_NUMBER"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true` incoming calls from private numbers are allowed."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true` incoming calls from unavailable numbers are allo"),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="(required) When set to `true` sequential ringing is enabled for calls t"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add User Sequential Ring Criteria\n\nExample --json-body:\n  '{"callsFrom":"SELECT_PHONE_NUMBERS","ringEnabled":true,"scheduleName":"...","scheduleType":"holidays","scheduleLevel":"GROUP","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if ring_enabled is not None:
            body["ringEnabled"] = ring_enabled
        _missing = [f for f in ['callsFrom', 'ringEnabled'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("show-criteria-sequential-ring")
def show_criteria_sequential_ring(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Sequential Ring Criteria Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing/criteria/{id}"
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



@app.command("update-criteria-sequential-ring")
def update_criteria_sequential_ring(
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, means this criteria applies for anonymous calle"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, means this criteria applies for unavailable cal"),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="Determines whether sequential ring is applied for calls matc"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Sequential Ring Criteria Settings for User\n\nExample --json-body:\n  '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if ring_enabled is not None:
            body["ringEnabled"] = ring_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-criteria-sequential-ring")
def delete_criteria_sequential_ring(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Sequential Ring Criteria."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("list-simultaneous-ring")
def list_simultaneous_ring(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve My Simultaneous Ring Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing"
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
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-simultaneous-ring")
def update_simultaneous_ring(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Simultaneous Ring is enabled or not."),
    do_not_ring_if_on_call_enabled: bool = typer.Option(None, "--do-not-ring-if-on-call-enabled/--no-do-not-ring-if-on-call-enabled", help="When set to `true`, the configured phone numbers won't ring"),
    criterias_enabled: bool = typer.Option(None, "--criterias-enabled/--no-criterias-enabled", help="Controls whether the criteria for simultaneous ring are enab"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Simultaneous Ring Settings\n\nExample --json-body:\n  '{"enabled":true,"doNotRingIfOnCallEnabled":true,"phoneNumbers":[{"phoneNumber":"...","answerConfirmationEnabled":"..."}],"criteriasEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if do_not_ring_if_on_call_enabled is not None:
            body["doNotRingIfOnCallEnabled"] = do_not_ring_if_on_call_enabled
        if criterias_enabled is not None:
            body["criteriasEnabled"] = criterias_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-criteria-simultaneous-ring")
def show_criteria_simultaneous_ring(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve My Simultaneous Ring Criteria."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing/criteria/{id}"
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



@app.command("update-criteria-simultaneous-ring")
def update_criteria_simultaneous_ring(
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule which determines when the simultaneous"),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, the criteria applies to calls from anonymous ca"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, the criteria applies to calls from unavailable"),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="When set to `true` simultaneous ringing is enabled for calls"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Simultaneous Ring Criteria\n\nExample --json-body:\n  '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing/criteria/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if ring_enabled is not None:
            body["ringEnabled"] = ring_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-criteria-simultaneous-ring")
def delete_criteria_simultaneous_ring(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete My Simultaneous Ring Criteria."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing/criteria/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("create-criteria-simultaneous-ring")
def create_criteria_simultaneous_ring(
    schedule_name: str = typer.Option(None, "--schedule-name", help="(required) Name of the schedule which determines when the simultaneous"),
    schedule_type: str = typer.Option(None, "--schedule-type", help="(required) Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="(required) Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, the criteria applies to calls from anonymous ca"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, the criteria applies to calls from unavailable"),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="(required) When set to `true` simultaneous ringing is enabled for calls"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create My Simultaneous Ring Criteria\n\nExample --json-body:\n  '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","ringEnabled":true,"anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing/criteria"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if ring_enabled is not None:
            body["ringEnabled"] = ring_enabled
        _missing = [f for f in ['scheduleName', 'scheduleType', 'scheduleLevel', 'callsFrom', 'ringEnabled'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("list-numbers")
def list_numbers(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve My Guest Calling Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/guestCalling/numbers"
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
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


