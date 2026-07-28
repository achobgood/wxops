import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling my-call-settings.")


@app.command("list", short_help="Get List Available Preferred Answer Endpoints.")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("endpoints", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type')], limit=limit)



@app.command("list-available-preferred-answer-endpoints", short_help="Get My Secondary Line Owner's Available Preferred Answer Endpoint List.")
def list_available_preferred_answer_endpoints(
    line_owner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Available Preferred Answer Endpoint List.\n\n\b\nExample: wxcli my-call-settings list-available-preferred-answer-endpoints LINE_OWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{line_owner_id}/availablePreferredAnswerEndpoints"
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
    items = result.get("endpoints", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type')], limit=limit)



@app.command("show", short_help="Get Preferred Answer Endpoint.")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/preferredAnswerEndpoint"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"preferredAnswerEndpointId":"..."}'

@app.command("update", short_help="Modify Preferred Answer Endpoint.")
def update(
    preferred_answer_endpoint_id: str = typer.Option(None, "--preferred-answer-endpoint-id", help="Person’s preferred answer endpoint."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Preferred Answer Endpoint.\n\n\b\nExample: wxcli my-call-settings update --preferred-answer-endpoint-id PREFERRED_ANSWER_ENDPOINT_ID\n\n\b\nExample --json-body: '{"preferredAnswerEndpointId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/preferredAnswerEndpoint"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if preferred_answer_endpoint_id is not None:
            body["preferredAnswerEndpointId"] = preferred_answer_endpoint_id
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-preferred-answer-endpoint", short_help="Get My Secondary Line Owner's Preferred Answer Endpoint.")
def show_preferred_answer_endpoint(
    line_owner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Preferred Answer Endpoint.\n\n\b\nExample: wxcli my-call-settings show-preferred-answer-endpoint LINE_OWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{line_owner_id}/preferredAnswerEndpoint"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_PREFERRED_ANSWER_ENDPOINT = '{"preferredAnswerEndpointId":"..."}'

@app.command("update-preferred-answer-endpoint", short_help="Modify My Secondary Line Owner's Preferred Answer Endpoint.")
def update_preferred_answer_endpoint(
    line_owner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    preferred_answer_endpoint_id: str = typer.Option(None, "--preferred-answer-endpoint-id", help="Person’s preferred answer endpoint."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Preferred Answer Endpoint.\n\n\b\nExample: wxcli my-call-settings update-preferred-answer-endpoint LINE_OWNER_ID --preferred-answer-endpoint-id PREFERRED_ANSWER_ENDPOINT_ID\n\n\b\nExample --json-body: '{"preferredAnswerEndpointId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PREFERRED_ANSWER_ENDPOINT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{line_owner_id}/preferredAnswerEndpoint"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if preferred_answer_endpoint_id is not None:
            body["preferredAnswerEndpointId"] = preferred_answer_endpoint_id
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
        emit({"status": "updated", "id": line_owner_id}, output=output, fields=fields)



@app.command("show-webex-go-override", short_help="Get My WebexGoOverride Settings.")
def show_webex_go_override(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My WebexGoOverride Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/webexGoOverride"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_WEBEX_GO_OVERRIDE = '{"enabled":true}'

@app.command("update-webex-go-override", short_help="Modify My WebexGoOverride Settings.")
def update_webex_go_override(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="True if the \"Mobile User Aware\" override setting for Do Not Disturb feature is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My WebexGoOverride Settings.\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_WEBEX_GO_OVERRIDE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/webexGoOverride"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-caller-id-settings", short_help="Get My Caller ID Settings.")
def show_caller_id_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callerId"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALLER_ID_SETTINGS = '{"callingLineIdDeliveryBlockingEnabled":true,"connectedLineIdentificationRestrictionEnabled":true}'

@app.command("update-caller-id-settings", short_help="Modify My Caller ID Settings.")
def update_caller_id_settings(
    calling_line_id_delivery_blocking_enabled: bool = typer.Option(None, "--calling-line-id-delivery-blocking-enabled/--no-calling-line-id-delivery-blocking-enabled", help="If `true`, the user's name and phone number are not shown to people they call."),
    connected_line_identification_restriction_enabled: bool = typer.Option(None, "--connected-line-identification-restriction-enabled/--no-connected-line-identification-restriction-enabled", help="If `true`, the user's name and phone number are not shown when receiving a call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Caller ID Settings.\n\n\b\nExample --json-body: '{"callingLineIdDeliveryBlockingEnabled":true,"connectedLineIdentificationRestrictionEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALLER_ID_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callerId"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-caller-id-secondary-lines", short_help="Get My Secondary Line Owner Caller ID Settings.")
def show_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Caller ID Settings.\n\n\b\nExample: wxcli my-call-settings show-caller-id-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callerId"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALLER_ID_SECONDARY_LINES = '{"callingLineIdDeliveryBlockingEnabled":true,"connectedLineIdentificationRestrictionEnabled":true}'

@app.command("update-caller-id-secondary-lines", short_help="Modify My Secondary Line Owner Caller ID Settings.")
def update_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    calling_line_id_delivery_blocking_enabled: bool = typer.Option(None, "--calling-line-id-delivery-blocking-enabled/--no-calling-line-id-delivery-blocking-enabled", help="If `true`, the user's name and phone number are not shown to people they call."),
    connected_line_identification_restriction_enabled: bool = typer.Option(None, "--connected-line-identification-restriction-enabled/--no-connected-line-identification-restriction-enabled", help="If `true`, the user's name and phone number are not shown when receiving a call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner Caller ID Settings.\n\n\b\nExample: wxcli my-call-settings update-caller-id-secondary-lines LINEOWNER_ID\n\n\b\nExample --json-body: '{"callingLineIdDeliveryBlockingEnabled":true,"connectedLineIdentificationRestrictionEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALLER_ID_SECONDARY_LINES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callerId"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": lineowner_id}, output=output, fields=fields)



@app.command("show-selected-caller-id-settings", short_help="Read My Selected Caller ID Settings.")
def show_selected_caller_id_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read My Selected Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectedCallerId"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SELECTED_CALLER_ID_SETTINGS = '{"selected":{"type":"DEFAULT_CLID","id":"...","directNumber":"..."}}'

@app.command("update-selected-caller-id-settings", short_help="Configure My Selected Caller ID Settings.")
def update_selected_caller_id_settings(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure My Selected Caller ID Settings.\n\n\b\nExample --json-body: '{"selected":{"type":"DEFAULT_CLID","id":"...","directNumber":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTED_CALLER_ID_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectedCallerId"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-selected-caller-id-secondary-lines", short_help="Get My Secondary Line Owner's Selected Caller ID Settings.")
def show_selected_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Selected Caller ID Settings.\n\n\b\nExample: wxcli my-call-settings show-selected-caller-id-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/selectedCallerId"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SELECTED_CALLER_ID_SECONDARY_LINES = '{"selected":{"type":"DEFAULT_CLID","id":"...","directNumber":"..."}}'

@app.command("update-selected-caller-id-secondary-lines", short_help="Modify My Secondary Line Owner's Selected Caller ID Settings.")
def update_selected_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Selected Caller ID Settings.\n\n\b\nExample: wxcli my-call-settings update-selected-caller-id-secondary-lines LINEOWNER_ID\n\n\b\nExample --json-body: '{"selected":{"type":"DEFAULT_CLID","id":"...","directNumber":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTED_CALLER_ID_SECONDARY_LINES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/selectedCallerId"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated", "id": lineowner_id}, output=output, fields=fields)



@app.command("list-available-caller-ids-settings", short_help="Get My Available Caller ID List.")
def list_available_caller_ids_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("availableCallerIds", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Direct Number', 'directNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-available-caller-ids-secondary-lines", short_help="Get My Secondary Line Owner's Available Caller ID List.")
def list_available_caller_ids_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Available Caller ID List.\n\n\b\nExample: wxcli my-call-settings list-available-caller-ids-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/availableCallerIds"
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
    items = result.get("availableCallerIds", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Direct Number', 'directNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-endpoints", short_help="Read the List of My Endpoints.")
def list_endpoints(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("endpoints", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Auto And Forced Answer Enabled', 'autoAndForcedAnswerEnabled'), ('Owner ID', 'ownerId')], limit=limit)



@app.command("show-endpoints", short_help="Get My Endpoints Details.")
def show_endpoints(
    endpoint_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli my-call-settings list-endpoints"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Endpoints Details.\n\n\b\nExample: wxcli my-call-settings show-endpoints ENDPOINT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/endpoints/{endpoint_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ENDPOINTS = '{"mobilitySettings":{"alertingEnabled":true}}'

@app.command("update-endpoints", short_help="Modify My Endpoints Details.")
def update_endpoints(
    endpoint_id: str = typer.Argument(help="Webex CALLING_DEVICE id, from: wxcli my-call-settings list-endpoints"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Endpoints Details.\n\n\b\nExample: wxcli my-call-settings update-endpoints ENDPOINT_ID\n\n\b\nExample --json-body: '{"mobilitySettings":{"alertingEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ENDPOINTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/endpoints/{endpoint_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated", "id": endpoint_id}, output=output, fields=fields)



@app.command("show-call-recording-settings", short_help="Get My Call Recording Settings.")
def show_call_recording_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Recording Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callRecording"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-call-recording-secondary-lines", short_help="Get My Secondary Line Owner's Call Recording Settings.")
def show_call_recording_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Call Recording Settings.\n\n\b\nExample: wxcli my-call-settings show-call-recording-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callRecording"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-me", short_help="Get My Own Details.")
def show_me(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Own Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-feature-access-code-settings", short_help="Get My Feature Access Codes.")
def list_feature_access_code_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("featureAccessCodeList", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Name', 'name'), ('Code', 'code'), ('Alternate Code', 'alternateCode')], limit=limit)



@app.command("list-feature-access-code-secondary-lines", short_help="Get My Feature Access Codes For Secondary Line Owner.")
def list_feature_access_code_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Feature Access Codes For Secondary Line Owner.\n\n\b\nExample: wxcli my-call-settings list-feature-access-code-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/featureAccessCode"
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
    items = result.get("featureAccessCodeList", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Name', 'name'), ('Code', 'code'), ('Alternate Code', 'alternateCode')], limit=limit)



@app.command("list-assigned-assistants", short_help="Get My Executive Assigned Assistants.")
def list_assigned_assistants(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("assistants", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Direct Number', 'directNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE_ASSIGNED_ASSISTANTS = '{"allowOptInOutEnabled":true,"assistantIds":["..."]}'

@app.command("update-assigned-assistants", short_help="Modify My Executive Assigned Assistants.")
def update_assigned_assistants(
    allow_opt_in_out_enabled: bool = typer.Option(None, "--allow-opt-in-out-enabled/--no-allow-opt-in-out-enabled", help="If `true`, the executive can allow assistants to opt in or out of managing calls."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Executive Assigned Assistants.\n\n\b\nExample --json-body: '{"allowOptInOutEnabled":true,"assistantIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ASSIGNED_ASSISTANTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/executive/assignedAssistants"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if allow_opt_in_out_enabled is not None:
            body["allowOptInOutEnabled"] = allow_opt_in_out_enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("list-available-assistants", short_help="Get My Executive Available Assistants.")
def list_available_assistants(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("assistants", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Direct Number', 'directNumber'), ('Extension', 'extension')], limit=limit)



@app.command("list-assistant", short_help="Get My Executive Assistant Settings.")
def list_assistant(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("executives", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Direct Number', 'directNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_UPDATE_ASSISTANT = '{"forwardFilteredCallsEnabled":true,"forwardToPhoneNumber":"...","executives":[{"personId":"...","optInEnabled":"..."}]}'

@app.command("update-assistant", short_help="Modify My Executive Assistant Settings.")
def update_assistant(
    forward_filtered_calls_enabled: bool = typer.Option(None, "--forward-filtered-calls-enabled/--no-forward-filtered-calls-enabled", help="If `true`, filtered calls to assistant are forwarded to the `forwardToPhoneNumber`."),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="Phone number to forward the filtered calls to. Mandatory if `forwardFilteredCallsEnabled` is set to true."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Executive Assistant Settings.\n\n\b\nExample --json-body: '{"forwardFilteredCallsEnabled":true,"forwardToPhoneNumber":"...","executives":[{"personId":"...","optInEnabled":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ASSISTANT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/executive/assistant"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("list-services-settings", short_help="Get My Calling Services List.")
def list_services_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("services", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-services-secondary-lines", short_help="Get My Secondary Line Owner Calling Services List.")
def list_services_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Calling Services List.\n\n\b\nExample: wxcli my-call-settings list-services-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/services"
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
    items = result.get("services", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-single-number-reach", short_help="Get User's Single Number Reach Settings.")
def list_single_number_reach(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("numbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Phone Number', 'phoneNumber'), ('Enabled', 'enabled'), ('Do Not Forward Calls Enabled', 'doNotForwardCallsEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SINGLE_NUMBER_REACH = '{"alertAllLocationsForClickToDialCallsEnabled":true}'

@app.command("update-single-number-reach", short_help="Modify User's Single Number Reach Settings.")
def update_single_number_reach(
    alert_all_locations_for_click_to_dial_calls_enabled: bool = typer.Option(None, "--alert-all-locations-for-click-to-dial-calls-enabled/--no-alert-all-locations-for-click-to-dial-calls-enabled", help="If `true`, all locations will be alerted for click-to-dial calls."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify User's Single Number Reach Settings.\n\n\b\nExample --json-body: '{"alertAllLocationsForClickToDialCallsEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SINGLE_NUMBER_REACH), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if alert_all_locations_for_click_to_dial_calls_enabled is not None:
            body["alertAllLocationsForClickToDialCallsEnabled"] = alert_all_locations_for_click_to_dial_calls_enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"phoneNumber":"...","name":"...","enabled":true,"doNotForwardCallsEnabled":true,"answerConfirmationEnabled":true}'

@app.command("create", short_help="Add phone number as User's Single Number Reach.")
def create(
    phone_number: str = typer.Option(None, "--phone-number", help="(required) Phone number."),
    name: str = typer.Option(None, "--name", help="(required) Name associated with the phone number."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="(required) If `true`, the phone number is enabled."),
    do_not_forward_calls_enabled: bool = typer.Option(None, "--do-not-forward-calls-enabled/--no-do-not-forward-calls-enabled", help="Note that this setting attempts to prevent the Single Number Reach (SNR) destination from forwarding the call. The SNR destination may or may not respect the indication provided hence, it may still be forwarded, and this setting has no impact on the user's own forwarding services."),
    answer_confirmation_enabled: bool = typer.Option(None, "--answer-confirmation-enabled/--no-answer-confirmation-enabled", help="If `true`, answer confirmation is enabled. The default value is `false`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add phone number as User's Single Number Reach.\n\n\b\nExample: wxcli my-call-settings create --phone-number PHONE_NUMBER --name NAME --enabled\n\n\b\nExample --json-body: '{"phoneNumber":"...","name":"...","enabled":true,"doNotForwardCallsEnabled":true,"answerConfirmationEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach/numbers"
    if json_body:
        body = load_json_body(json_body)
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



_BODY_SKELETON_UPDATE_NUMBERS = '{"phoneNumber":"...","name":"...","enabled":true,"doNotForwardCallsEnabled":true,"answerConfirmationEnabled":true}'

@app.command("update-numbers", short_help="Modify User's Single Number Reach Contact Settings.")
def update_numbers(
    phone_number_id: str = typer.Argument(help="Webex PHONE_NUMBER id"),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number."),
    name: str = typer.Option(None, "--name", help="Name associated with the phone number."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="If `true`, the phone number is enabled."),
    do_not_forward_calls_enabled: bool = typer.Option(None, "--do-not-forward-calls-enabled/--no-do-not-forward-calls-enabled", help="If `true`, calls are not forwarded."),
    answer_confirmation_enabled: bool = typer.Option(None, "--answer-confirmation-enabled/--no-answer-confirmation-enabled", help="If `true`, answer confirmation is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify User's Single Number Reach Contact Settings.\n\n\b\nExample: wxcli my-call-settings update-numbers PHONE_NUMBER_ID --phone-number PHONE_NUMBER --name NAME --enabled --do-not-forward-calls-enabled --answer-confirmation-enabled\n\n\b\nExample --json-body: '{"phoneNumber":"...","name":"...","enabled":true,"doNotForwardCallsEnabled":true,"answerConfirmationEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach/numbers/{phone_number_id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": phone_number_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete User's Single Number Reach Contact Settings.")
def delete(
    phone_number_id: str = typer.Argument(help="Webex PHONE_NUMBER id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete User's Single Number Reach Contact Settings.\n\n\b\nExample: wxcli my-call-settings delete PHONE_NUMBER_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {phone_number_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach/numbers/{phone_number_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {phone_number_id}")
    else:
        emit({"status": "deleted", "id": phone_number_id}, output=output, fields=fields)



@app.command("show-call-forwarding-settings", short_help="Read My Call Forwarding Settings.")
def show_call_forwarding_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read My Call Forwarding Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callForwarding"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_FORWARDING_SETTINGS = '{"callForwarding":{"always":{"enabled":"...","destination":"...","ringReminderEnabled":"...","destinationVoicemailEnabled":"..."},"busy":{"enabled":"...","destination":"...","destinationVoicemailEnabled":"..."},"noAnswer":{"enabled":"...","destination":"...","numberOfRings":"...","destinationVoicemailEnabled":"..."}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'

@app.command("update-call-forwarding-settings", short_help="Configure My Call Forwarding Settings.")
def update_call_forwarding_settings(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure My Call Forwarding Settings.\n\n\b\nExample --json-body: '{"callForwarding":{"always":{"enabled":"...","destination":"...","ringReminderEnabled":"...","destinationVoicemailEnabled":"..."},"busy":{"enabled":"...","destination":"...","destinationVoicemailEnabled":"..."},"noAnswer":{"enabled":"...","destination":"...","numberOfRings":"...","destinationVoicemailEnabled":"..."}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_FORWARDING_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callForwarding"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-call-forwarding-secondary-lines", short_help="Get My Secondary Line Owner's Call Forwarding Settings.")
def show_call_forwarding_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Call Forwarding Settings.\n\n\b\nExample: wxcli my-call-settings show-call-forwarding-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callForwarding"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_FORWARDING_SECONDARY_LINES = '{"callForwarding":{"always":{"enabled":"...","destination":"...","ringReminderEnabled":"...","destinationVoicemailEnabled":"..."},"busy":{"enabled":"...","destination":"...","destinationVoicemailEnabled":"..."},"noAnswer":{"enabled":"...","destination":"...","numberOfRings":"...","destinationVoicemailEnabled":"..."}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'

@app.command("update-call-forwarding-secondary-lines", short_help="Modify My Secondary Line Owner's Call Forwarding Settings.")
def update_call_forwarding_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Call Forwarding Settings.\n\n\b\nExample: wxcli my-call-settings update-call-forwarding-secondary-lines LINEOWNER_ID\n\n\b\nExample --json-body: '{"callForwarding":{"always":{"enabled":"...","destination":"...","ringReminderEnabled":"...","destinationVoicemailEnabled":"..."},"busy":{"enabled":"...","destination":"...","destinationVoicemailEnabled":"..."},"noAnswer":{"enabled":"...","destination":"...","numberOfRings":"...","destinationVoicemailEnabled":"..."}},"businessContinuity":{"enabled":true,"destination":"...","destinationVoicemailEnabled":true}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_FORWARDING_SECONDARY_LINES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callForwarding"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated", "id": lineowner_id}, output=output, fields=fields)



@app.command("list-call-pickup-group-settings", short_help="Get My Call Pickup Group Settings.")
def list_call_pickup_group_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("memberList", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Type', 'type'), ('Last Name', 'lastName'), ('Department Name', 'departmentName')], limit=limit)



@app.command("list-call-pickup-group-secondary-lines", short_help="Get My Secondary Line Owner Call Pickup Group Settings.")
def list_call_pickup_group_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Call Pickup Group Settings.\n\n\b\nExample: wxcli my-call-settings list-call-pickup-group-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callPickupGroup"
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
    items = result.get("memberList", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Type', 'type'), ('Last Name', 'lastName'), ('Department Name', 'departmentName')], limit=limit)



@app.command("list-call-park-settings", short_help="Get My Call Park Settings.")
def list_call_park_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("memberList", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Type', 'type'), ('First Name', 'firstName'), ('Last Name', 'lastName')], limit=limit)



@app.command("list-call-park-secondary-lines", short_help="Get My Secondary Line Owner Call Park Settings.")
def list_call_park_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Call Park Settings.\n\n\b\nExample: wxcli my-call-settings list-call-park-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callPark"
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
    items = result.get("memberList", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Type', 'type'), ('First Name', 'firstName'), ('Last Name', 'lastName')], limit=limit)



@app.command("show-voicemail-settings", short_help="Read Voicemail Settings for a Person.")
def show_voicemail_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Voicemail Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/voicemail"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_VOICEMAIL_SETTINGS = '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."}}'

@app.command("update-voicemail-settings", short_help="Configure Voicemail Settings for a Person.")
def update_voicemail_settings(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Voicemail is enabled or disabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Voicemail Settings for a Person.\n\n\b\nExample --json-body: '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VOICEMAIL_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/voicemail"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-voicemail-secondary-lines", short_help="Get My Secondary Line Owner's Voicemail Settings.")
def show_voicemail_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Voicemail Settings.\n\n\b\nExample: wxcli my-call-settings show-voicemail-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/voicemail"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_VOICEMAIL_SECONDARY_LINES = '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."}}'

@app.command("update-voicemail-secondary-lines", short_help="Modify My Secondary Line Owner's Voicemail Settings.")
def update_voicemail_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Voicemail is enabled or disabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Voicemail Settings.\n\n\b\nExample: wxcli my-call-settings update-voicemail-secondary-lines LINEOWNER_ID\n\n\b\nExample --json-body: '{"notifications":{"enabled":true,"destination":"...","smsDestination":"..."},"transferToNumber":{"enabled":true,"destination":"..."},"enabled":true,"sendAllCalls":{"enabled":true},"sendBusyCalls":{"enabled":true,"greeting":"DEFAULT"},"sendUnansweredCalls":{"enabled":true,"greeting":"DEFAULT","numberOfRings":0},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"messageStorage":{"mwiEnabled":true,"storageType":"INTERNAL","externalEmail":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VOICEMAIL_SECONDARY_LINES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/voicemail"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated", "id": lineowner_id}, output=output, fields=fields)



@app.command("list-call-block", short_help="Get My Call Block Settings.")
def list_call_block(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("numbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Phone Number', 'phoneNumber')], limit=limit)



_BODY_SKELETON_CREATE_NUMBERS = '{"phoneNumber":"..."}'

@app.command("create-numbers", short_help="Add a phone number to user's Call Block List.")
def create_numbers(
    phone_number: str = typer.Option(None, "--phone-number", help="(required) Phone number which is blocked by user."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a phone number to user's Call Block List.\n\n\b\nExample: wxcli my-call-settings create-numbers --phone-number PHONE_NUMBER\n\n\b\nExample --json-body: '{"phoneNumber":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callBlock/numbers"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-numbers", short_help="Get My Call Block State For Specific Number.")
def show_numbers(
    phone_number_id: str = typer.Argument(help="Webex PHONE_NUMBER id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Block State For Specific Number.\n\n\b\nExample: wxcli my-call-settings show-numbers PHONE_NUMBER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callBlock/numbers/{phone_number_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("delete-numbers", short_help="Delete User Call Block Number.")
def delete_numbers(
    phone_number_id: str = typer.Argument(help="Webex PHONE_NUMBER id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete User Call Block Number.\n\n\b\nExample: wxcli my-call-settings delete-numbers PHONE_NUMBER_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {phone_number_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callBlock/numbers/{phone_number_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {phone_number_id}")
    else:
        emit({"status": "deleted", "id": phone_number_id}, output=output, fields=fields)



@app.command("list-monitoring", short_help="Get My Monitoring Settings.")
def list_monitoring(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("monitoredElements", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Member', 'member.displayName'), ('Email', 'member.email'), ('Call Park Extension', 'callparkextension.name'), ('Extension', 'callparkextension.extension'), ('Speed Dial', 'speedDial.displayName')], limit=limit)



@app.command("list-queues-settings", short_help="Get My Call Center Settings.")
def list_queues_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("queues", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Phone Number', 'phoneNumber'), ('Has Cx Essentials', 'hasCxEssentials'), ('Available', 'available'), ('Skill Level', 'skillLevel')], limit=limit)



_BODY_SKELETON_UPDATE_QUEUES_SETTINGS = '{"agentACDState":"SIGN_IN","queues":[{"id":"...","available":"..."}]}'

@app.command("update-queues-settings", short_help="Modify My Call Center Settings.")
def update_queues_settings(
    agent_acd_state: str = typer.Option(None, "--agent-acd-state", help="Choices: SIGN_IN, SIGN_OUT, AVAILABLE, UNAVAILABLE, WRAP_UP"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Call Center Settings.\n\n\b\nExample --json-body: '{"agentACDState":"SIGN_IN","queues":[{"id":"...","available":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_QUEUES_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/queues"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if agent_acd_state is not None:
            body["agentACDState"] = agent_acd_state
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("list-queues-secondary-lines", short_help="Get My Secondary Line Owner's Call Center Settings.")
def list_queues_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Call Center Settings.\n\n\b\nExample: wxcli my-call-settings list-queues-secondary-lines LINEOWNER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/queues"
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
    items = result.get("queues", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Phone Number', 'phoneNumber'), ('Has Cx Essentials', 'hasCxEssentials'), ('Available', 'available'), ('Skill Level', 'skillLevel')], limit=limit)



_BODY_SKELETON_UPDATE_QUEUES_SECONDARY_LINES = '{"agentACDState":"SIGN_IN","queues":[{"id":"...","available":"..."}]}'

@app.command("update-queues-secondary-lines", short_help="Modify My Secondary Line Owner's Call Center Settings.")
def update_queues_secondary_lines(
    lineowner_id: str = typer.Argument(help="Webex VIRTUAL_LINE id"),
    agent_acd_state: str = typer.Option(None, "--agent-acd-state", help="Choices: SIGN_IN, SIGN_OUT, AVAILABLE, UNAVAILABLE, WRAP_UP"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Call Center Settings.\n\n\b\nExample: wxcli my-call-settings update-queues-secondary-lines LINEOWNER_ID\n\n\b\nExample --json-body: '{"agentACDState":"SIGN_IN","queues":[{"id":"...","available":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_QUEUES_SECONDARY_LINES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/queues"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if agent_acd_state is not None:
            body["agentACDState"] = agent_acd_state
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
        emit({"status": "updated", "id": lineowner_id}, output=output, fields=fields)



@app.command("show-call-captions", short_help="Get my call captions settings.")
def show_call_captions(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get my call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callCaptions"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-priority-alert", short_help="Get Priority Alert Settings.")
def list_priority_alert(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Schedule Name', 'scheduleName'), ('Source', 'source'), ('Notification Enabled', 'notificationEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_PRIORITY_ALERT = '{"enabled":true}'

@app.command("update-priority-alert", short_help="Modify Priority Alert Settings for User.")
def update_priority_alert(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Priority Alert feature is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Priority Alert Settings for User.\n\n\b\nExample: wxcli my-call-settings update-priority-alert --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PRIORITY_ALERT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_PRIORITY_ALERT = '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'

@app.command("create-criteria-priority-alert", short_help="Add a Priority Alert Criteria.")
def create_criteria_priority_alert(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    notification_enabled: bool = typer.Option(None, "--notification-enabled/--no-notification-enabled", help="Determines whether priority alerting is applied for calls matching this criteria. If `true`, priority alerting is applied. If `false`, this criteria acts as a 'Don't Alert' rule, preventing priority alerting. Criteria with `notificationEnabled` set to `false` (Don't Alert) take precedence over..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a Priority Alert Criteria.\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_PRIORITY_ALERT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert/criteria"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-criteria-priority-alert", short_help="Get Priority Alert Criteria Settings.")
def show_criteria_priority_alert(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Priority Alert Criteria Settings.\n\n\b\nExample: wxcli my-call-settings show-criteria-priority-alert ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_PRIORITY_ALERT = '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'

@app.command("update-criteria-priority-alert", short_help="Modify Settings for a Priority Alert Criteria.")
def update_criteria_priority_alert(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    notification_enabled: bool = typer.Option(None, "--notification-enabled/--no-notification-enabled", help="Determines whether priority alerting is applied for calls matching this criteria. If `true`, priority alerting is applied. If `false`, this criteria acts as a 'Don't Alert' rule, preventing priority alerting. Criteria with `notificationEnabled` set to `false` (Don't Alert) take precedence over..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Settings for a Priority Alert Criteria.\n\n\b\nExample: wxcli my-call-settings update-criteria-priority-alert ID\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_PRIORITY_ALERT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert/criteria/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-priority-alert", short_help="Delete a Priority Alert Criteria.")
def delete_criteria_priority_alert(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Priority Alert Criteria.\n\n\b\nExample: wxcli my-call-settings delete-criteria-priority-alert ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert/criteria/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-schedules", short_help="Get User (and Location) Schedules.")
def list_schedules(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("schedules", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Level', 'level')], limit=limit)



_BODY_SKELETON_CREATE_SCHEDULES = '{"type":"businessHours","name":"...","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":"...","recurrence":"..."}]}'

@app.command("create-schedules", short_help="Add a User level Schedule for Call Settings.")
def create_schedules(
    type_param: str = typer.Option(None, "--type", help="(required) Choices: businessHours, holidays"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the schedule."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a User level Schedule for Call Settings.\n\n\b\nExample: wxcli my-call-settings create-schedules --type businessHours --name NAME\n\n\b\nExample --json-body: '{"type":"businessHours","name":"...","events":[{"name":"...","startDate":"...","endDate":"...","startTime":"...","endTime":"...","allDayEnabled":"...","recurrence":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SCHEDULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-schedules-me", short_help="Get User Schedule.")
def show_schedules_me(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli my-call-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli my-call-settings list-schedules"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User Schedule.\n\n\b\nExample: wxcli my-call-settings show-schedules-me businessHours SCHEDULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SCHEDULES = '{"name":"...","events":[{"name":"...","startDate":"...","endDate":"...","allDayEnabled":"...","newName":"...","startTime":"...","endTime":"...","recurrence":"..."}]}'

@app.command("update-schedules", short_help="Modify User Schedule.")
def update_schedules(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli my-call-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli my-call-settings list-schedules"),
    name: str = typer.Option(None, "--name", help="Name of the schedule."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify User Schedule.\n\n\b\nExample: wxcli my-call-settings update-schedules businessHours SCHEDULE_ID --name NAME\n\n\b\nExample --json-body: '{"name":"...","events":[{"name":"...","startDate":"...","endDate":"...","allDayEnabled":"...","newName":"...","startTime":"...","endTime":"...","recurrence":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SCHEDULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
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
        emit({"status": "updated", "id": schedule_id}, output=output, fields=fields)



@app.command("delete-schedules", short_help="Delete a User Schedule.")
def delete_schedules(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli my-call-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli my-call-settings list-schedules"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a User Schedule.\n\n\b\nExample: wxcli my-call-settings delete-schedules businessHours SCHEDULE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {schedule_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {schedule_id}")
    else:
        emit({"status": "deleted", "id": schedule_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_EVENTS = '{"name":"...","startDate":"...","endDate":"...","allDayEnabled":true,"startTime":"...","endTime":"...","recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":"..."},"recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."}}}'

@app.command("create-events", short_help="Add an event for a User Schedule.")
def create_events(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli my-call-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli my-call-settings list-schedules"),
    name: str = typer.Option(None, "--name", help="(required) Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="(required) Start Date of Event."),
    end_date: str = typer.Option(None, "--end-date", help="(required) End Date of Event."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of event."),
    end_time: str = typer.Option(None, "--end-time", help="End time of event."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="(required) An indication of whether given event is an all-day event or not."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add an event for a User Schedule.\n\n\b\nExample: wxcli my-call-settings create-events businessHours SCHEDULE_ID --name NAME --start-date START_DATE --end-date END_DATE --all-day-enabled\n\n\b\nExample --json-body: '{"name":"...","startDate":"...","endDate":"...","allDayEnabled":true,"startTime":"...","endTime":"...","recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":"..."},"recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_EVENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}/events"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-events", short_help="Get User Schedule Event.")
def show_events(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli my-call-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli my-call-settings list-schedules"),
    event_id: str = typer.Argument(help="Webex USER_SCHEDULE_EVENT id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User Schedule Event.\n\n\b\nExample: wxcli my-call-settings show-events businessHours SCHEDULE_ID EVENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_EVENTS = '{"name":"...","startDate":"...","endDate":"...","allDayEnabled":true,"newName":"...","startTime":"...","endTime":"...","recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":"..."},"recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."}}}'

@app.command("update-events", short_help="Modify User Schedule Event.")
def update_events(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli my-call-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli my-call-settings list-schedules"),
    event_id: str = typer.Argument(help="Webex USER_SCHEDULE_EVENT id"),
    name: str = typer.Option(None, "--name", help="Name for the event."),
    new_name: str = typer.Option(None, "--new-name", help="New Name for the event."),
    start_date: str = typer.Option(None, "--start-date", help="Start Date of Event."),
    end_date: str = typer.Option(None, "--end-date", help="End Date of Event."),
    start_time: str = typer.Option(None, "--start-time", help="Start time of event."),
    end_time: str = typer.Option(None, "--end-time", help="End time of event."),
    all_day_enabled: bool = typer.Option(None, "--all-day-enabled/--no-all-day-enabled", help="An indication of whether given event is an all-day event or not."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify User Schedule Event.\n\n\b\nExample: wxcli my-call-settings update-events businessHours SCHEDULE_ID EVENT_ID --name NAME --start-date START_DATE --end-date END_DATE --all-day-enabled\n\n\b\nExample --json-body: '{"name":"...","startDate":"...","endDate":"...","allDayEnabled":true,"newName":"...","startTime":"...","endTime":"...","recurrence":{"recurForEver":true,"recurEndDate":"...","recurEndOccurrence":0,"recurDaily":{"recurInterval":"..."},"recurWeekly":{"sunday":"...","monday":"...","tuesday":"...","wednesday":"...","thursday":"...","friday":"...","saturday":"..."}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EVENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": event_id}, output=output, fields=fields)



@app.command("delete-events", short_help="Delete User a Schedule Event.")
def delete_events(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli my-call-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli my-call-settings list-schedules"),
    event_id: str = typer.Argument(help="Webex USER_SCHEDULE_EVENT id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete User a Schedule Event.\n\n\b\nExample: wxcli my-call-settings delete-events businessHours SCHEDULE_ID EVENT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {event_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/schedules/{schedule_type}/{schedule_id}/events/{event_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {event_id}")
    else:
        emit({"status": "deleted", "id": event_id}, output=output, fields=fields)



@app.command("show-schedules-locations", short_help="Get User's Location Level Schedule.")
def show_schedules_locations(
    schedule_type: str = typer.Argument(help="one of: businessHours|holidays, from: wxcli my-call-settings list-schedules"),
    schedule_id: str = typer.Argument(help="Webex USER_SCHEDULE id, from: wxcli my-call-settings list-schedules"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User's Location Level Schedule.\n\n\b\nExample: wxcli my-call-settings show-schedules-locations businessHours SCHEDULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/locations/schedules/{schedule_type}/{schedule_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-call-notify", short_help="Get Call Notify Settings for User.")
def list_call_notify(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Schedule Name', 'scheduleName'), ('Source', 'source'), ('Notification Enabled', 'notificationEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_CALL_NOTIFY = '{"enabled":true,"emailAddress":"..."}'

@app.command("update-call-notify", short_help="Modify Call Notify Settings for User.")
def update_call_notify(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Indicates whether the call notify feature should be enabled or disabled for the user."),
    email_address: str = typer.Option(None, "--email-address", help="Email Address to which call notifications to be received."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Call Notify Settings for User.\n\n\b\nExample: wxcli my-call-settings update-call-notify --enabled\n\n\b\nExample --json-body: '{"enabled":true,"emailAddress":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_NOTIFY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_CALL_NOTIFY = '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'

@app.command("create-criteria-call-notify", short_help="Add a Call Notify Criteria.")
def create_criteria_call_notify(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    notification_enabled: bool = typer.Option(None, "--notification-enabled/--no-notification-enabled", help="Determines whether call notification is applied for calls matching this criteria. If `true`, call notify is applied. If `false`, this criteria acts as a 'Don't Notify Me' rule, preventing call notification. Criteria with `notificationEnabled` set to `false` (Don't Notify Me) take precedence over..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a Call Notify Criteria.\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_CALL_NOTIFY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify/criteria"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-criteria-call-notify", short_help="Get Call Notify Criteria Settings.")
def show_criteria_call_notify(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Notify Criteria Settings.\n\n\b\nExample: wxcli my-call-settings show-criteria-call-notify ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_CALL_NOTIFY = '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'

@app.command("update-criteria-call-notify", short_help="Modify a Call Notify Criteria.")
def update_criteria_call_notify(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    notification_enabled: bool = typer.Option(None, "--notification-enabled/--no-notification-enabled", help="Determines whether call notification is applied for calls matching this criteria. If `true`, call notify is applied. If `false`, this criteria acts as a 'Don't Notify Me' rule, preventing call notification. Criteria with `notificationEnabled` set to `false` (Don't Notify Me) take precedence over..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Call Notify Criteria.\n\n\b\nExample: wxcli my-call-settings update-criteria-call-notify ID\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"notificationEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_CALL_NOTIFY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify/criteria/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-call-notify", short_help="Delete a Call Notify Criteria.")
def delete_criteria_call_notify(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Notify Criteria.\n\n\b\nExample: wxcli my-call-settings delete-criteria-call-notify ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callNotify/criteria/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-selective-accept", short_help="Get Selective Call Accept Settings for User.")
def list_selective_accept(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Schedule Name', 'scheduleName'), ('Source', 'source'), ('Accept Enabled', 'acceptEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SELECTIVE_ACCEPT = '{"enabled":true}'

@app.command("update-selective-accept", short_help="Modify Selective Call Accept Settings for User.")
def update_selective_accept(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="indicates whether selective accept is enabled or not."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Selective Call Accept Settings for User.\n\n\b\nExample: wxcli my-call-settings update-selective-accept --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_ACCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_ACCEPT = '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("create-criteria-selective-accept", short_help="Add User Selective Call Accept Criteria.")
def create_criteria_selective_accept(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    accept_enabled: bool = typer.Option(None, "--accept-enabled/--no-accept-enabled", help="(required) Boolean flag indicating if selective call accept is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add User Selective Call Accept Criteria.\n\n\b\nExample: wxcli my-call-settings create-criteria-selective-accept --calls-from ANY_PHONE_NUMBER --accept-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_ACCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept/criteria"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-criteria-selective-accept", short_help="Get Selective Call Accept Criteria Settings for User.")
def show_criteria_selective_accept(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Accept Criteria Settings for User.\n\n\b\nExample: wxcli my-call-settings show-criteria-selective-accept ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_ACCEPT = '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("update-criteria-selective-accept", short_help="Modify a Selective Call Accept Criteria.")
def update_criteria_selective_accept(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    accept_enabled: bool = typer.Option(None, "--accept-enabled/--no-accept-enabled", help="Boolean flag to enable/disable the selective accept criteria."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Selective Call Accept Criteria.\n\n\b\nExample: wxcli my-call-settings update-criteria-selective-accept ID --calls-from ANY_PHONE_NUMBER --accept-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","acceptEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_ACCEPT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept/criteria/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-selective-accept", short_help="Delete a Selective Call Accept Criteria.")
def delete_criteria_selective_accept(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Accept Criteria.\n\n\b\nExample: wxcli my-call-settings delete-criteria-selective-accept ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveAccept/criteria/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-assigned-numbers", short_help="Get Available Numbers for User's Location.")
def list_assigned_numbers(
    name: str = typer.Option(None, "--name", help="List numbers whose owner name contains this string."),
    phone_number: str = typer.Option(None, "--phone-number", help="List numbers whose phoneNumber contains this string."),
    extension: str = typer.Option(None, "--extension", help="List numbers whose extension contains this string."),
    order: str = typer.Option(None, "--order", help="Sort the list of numbers based on `lastName`, `dn`, `extension` either asc or desc."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('State', 'state'), ('Phone Number Type', 'phoneNumberType'), ('Toll Free Number', 'tollFreeNumber')], limit=limit)



_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_FORWARD = '{"forwardToPhoneNumber":"...","destinationVoicemailEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true}'

@app.command("create-criteria-selective-forward", short_help="Add a Selective Call Forwarding Criteria.")
def create_criteria_selective_forward(
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="The phone number to which calls are forwarded when the criteria conditions are met."),
    destination_voicemail_enabled: bool = typer.Option(None, "--destination-voicemail-enabled/--no-destination-voicemail-enabled", help="Indicates whether calls that meet the criteria are forwarded to the destination phone number's voicemail."),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    forward_enabled: bool = typer.Option(None, "--forward-enabled/--no-forward-enabled", help="Determines whether selective call forwarding is applied for calls matching this criteria. If `true`, the selective forwarding is applied. If `false`, this criteria acts as a 'Don't Forward' rule, preventing selectively forwarding of the calls. Criteria with `forwardEnabled` set to `false` (Don't..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add a Selective Call Forwarding Criteria.\n\n\b\nExample --json-body: '{"forwardToPhoneNumber":"...","destinationVoicemailEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_FORWARD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward/criteria"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-criteria-selective-forward", short_help="Get Settings for a Selective Call Forwarding Criteria.")
def show_criteria_selective_forward(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Settings for a Selective Call Forwarding Criteria.\n\n\b\nExample: wxcli my-call-settings show-criteria-selective-forward ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_FORWARD = '{"forwardToPhoneNumber":"...","destinationVoicemailEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true}'

@app.command("update-criteria-selective-forward", short_help="Modify Settings for a Selective Call Forwarding Criteria.")
def update_criteria_selective_forward(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help="The phone number to which calls are forwarded when the criteria conditions are met."),
    destination_voicemail_enabled: bool = typer.Option(None, "--destination-voicemail-enabled/--no-destination-voicemail-enabled", help="Indicates whether calls that meet the criteria are forwarded to the destination phone number's voicemail."),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, ANY_INTERNAL, ANY_EXTERNAL"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Indicates whether anonymous callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Indicates whether unavailable callers are included in this criteria. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    forward_enabled: bool = typer.Option(None, "--forward-enabled/--no-forward-enabled", help="Determines whether selective call forwarding is applied for calls matching this criteria. If `true`, the selective forwarding is applied. If `false`, this criteria acts as a 'Don't Forward' rule, preventing selectively forwarding of the calls. Criteria with `forwardEnabled` set to `false` (Don't..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Settings for a Selective Call Forwarding Criteria.\n\n\b\nExample: wxcli my-call-settings update-criteria-selective-forward ID\n\n\b\nExample --json-body: '{"forwardToPhoneNumber":"...","destinationVoicemailEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_FORWARD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward/criteria/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-selective-forward", short_help="Delete a Selective Call Forwarding Criteria.")
def delete_criteria_selective_forward(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Forwarding Criteria.\n\n\b\nExample: wxcli my-call-settings delete-criteria-selective-forward ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward/criteria/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-selective-forward", short_help="Get Selective Call Forward Settings for User.")
def list_selective_forward(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Schedule Name', 'scheduleName'), ('Source', 'source'), ('Ring Enabled', 'ringEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SELECTIVE_FORWARD = '{"enabled":true,"defaultPhoneNumberToForward":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true}'

@app.command("update-selective-forward", short_help="Modify Selective Call Forward Settings for User.")
def update_selective_forward(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the Selective Forward feature is enabled."),
    default_phone_number_to_forward: str = typer.Option(None, "--default-phone-number-to-forward", help="Enter the phone number to forward calls to during this schedule."),
    ring_reminder_enabled: bool = typer.Option(None, "--ring-reminder-enabled/--no-ring-reminder-enabled", help="When `true`, enables a ring reminder for such calls."),
    destination_voicemail_enabled: bool = typer.Option(None, "--destination-voicemail-enabled/--no-destination-voicemail-enabled", help="Enables forwarding for all calls to voicemail. This option is only available for internal phone numbers or extensions."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Selective Call Forward Settings for User.\n\n\b\nExample --json-body: '{"enabled":true,"defaultPhoneNumberToForward":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_FORWARD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveForward"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("list-selective-reject", short_help="Get Selective Call Reject Settings for User.")
def list_selective_reject(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("criteria", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Schedule Name', 'scheduleName'), ('Source', 'source'), ('Reject Enabled', 'rejectEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SELECTIVE_REJECT = '{"enabled":true}'

@app.command("update-selective-reject", short_help="Modify Selective Call Reject Settings for User.")
def update_selective_reject(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="if `true`, selective reject is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Selective Call Reject Settings for User.\n\n\b\nExample: wxcli my-call-settings update-selective-reject --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_REJECT = '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("create-criteria-selective-reject", short_help="Add User Selective Call Reject Criteria.")
def create_criteria_selective_reject(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, FORWARDED"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    reject_enabled: bool = typer.Option(None, "--reject-enabled/--no-reject-enabled", help="(required) Boolean flag to enable/disable rejection."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add User Selective Call Reject Criteria.\n\n\b\nExample: wxcli my-call-settings create-criteria-selective-reject --calls-from ANY_PHONE_NUMBER --reject-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SELECTIVE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject/criteria"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-anonymous-call-reject", short_help="Get Anonymous Call Rejection Settings for User.")
def show_anonymous_call_reject(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Anonymous Call Rejection Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/anonymousCallReject"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ANONYMOUS_CALL_REJECT = '{"enabled":true}'

@app.command("update-anonymous-call-reject", short_help="Modify Anonymous Call Rejection Settings for User.")
def update_anonymous_call_reject(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Indicates whether Anonymous Call Rejection is enabled or not."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Anonymous Call Rejection Settings for User.\n\n\b\nExample: wxcli my-call-settings update-anonymous-call-reject --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ANONYMOUS_CALL_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/anonymousCallReject"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-criteria-selective-reject", short_help="Get Selective Call Reject Criteria Settings for User.")
def show_criteria_selective_reject(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Reject Criteria Settings for User.\n\n\b\nExample: wxcli my-call-settings show-criteria-selective-reject ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_REJECT = '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("update-criteria-selective-reject", short_help="Modify a Selective Call Reject Criteria.")
def update_criteria_selective_reject(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to which the criteria is created."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS, FORWARDED"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="Boolean flag indicating if calls from custom numbers, private numbers are enabled."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="Boolean flag indicating if calls from custom numbers, unavailable numbers are enabled."),
    reject_enabled: bool = typer.Option(None, "--reject-enabled/--no-reject-enabled", help="Boolean flag to enable/disable rejection."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Selective Call Reject Criteria.\n\n\b\nExample: wxcli my-call-settings update-criteria-selective-reject ID --calls-from ANY_PHONE_NUMBER --reject-enabled\n\n\b\nExample --json-body: '{"callsFrom":"ANY_PHONE_NUMBER","rejectEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SELECTIVE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject/criteria/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-selective-reject", short_help="Delete a Selective Call Reject Criteria.")
def delete_criteria_selective_reject(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Reject Criteria.\n\n\b\nExample: wxcli my-call-settings delete-criteria-selective-reject ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectiveReject/criteria/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("show-call-waiting", short_help="Get Call Waiting Settings for User.")
def show_call_waiting(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Waiting Settings for User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callWaiting"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_WAITING = '{"enabled":true}'

@app.command("update-call-waiting", short_help="Modify Call Waiting Settings for User.")
def update_call_waiting(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable or disable Call Waiting for the user."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Call Waiting Settings for User.\n\n\b\nExample: wxcli my-call-settings update-call-waiting --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_WAITING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callWaiting"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("list-sequential-ring", short_help="Get Sequential Ring Settings for User.")
def list_sequential_ring(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Answer Confirmation Required Enabled', 'answerConfirmationRequiredEnabled'), ('Number Of Rings', 'numberOfRings')], limit=limit)



_BODY_SKELETON_UPDATE_SEQUENTIAL_RING = '{"enabled":true,"ringBaseLocationFirstEnabled":true,"baseLocationNumberOfRings":0,"continueIfBaseLocationIsBusyEnabled":true,"callsToVoicemailEnabled":true,"phoneNumbers":[{"answerConfirmationRequiredEnabled":"...","numberOfRings":"...","phoneNumber":"..."}]}'

@app.command("update-sequential-ring", short_help="Modify Sequential Ring Settings for User.")
def update_sequential_ring(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable or disable sequential ring for the user."),
    ring_base_location_first_enabled: bool = typer.Option(None, "--ring-base-location-first-enabled/--no-ring-base-location-first-enabled", help="When `true`, the user's own devices ring before sequential ring numbers."),
    base_location_number_of_rings: str = typer.Option(None, "--base-location-number-of-rings", help="Number of rings for the user's own devices. Minimum: 2, Maximum: 20."),
    continue_if_base_location_is_busy_enabled: bool = typer.Option(None, "--continue-if-base-location-is-busy-enabled/--no-continue-if-base-location-is-busy-enabled", help="When `true`, sequential ring continues even when the user is unavailable. It controls if we allow trying the sequential ring numbers when either a service for the user such as Do Not Disturb or Call Waiting sends the call to busy processing, or ringBaseLocationFirstEnabled is true but all the..."),
    calls_to_voicemail_enabled: bool = typer.Option(None, "--calls-to-voicemail-enabled/--no-calls-to-voicemail-enabled", help="When `true`, the caller is provided the option to press the # key to end the sequential ring service and send the call to no answer handling such as voicemail."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Sequential Ring Settings for User.\n\n\b\nExample: wxcli my-call-settings update-sequential-ring --enabled\n\n\b\nExample --json-body: '{"enabled":true,"ringBaseLocationFirstEnabled":true,"baseLocationNumberOfRings":0,"continueIfBaseLocationIsBusyEnabled":true,"callsToVoicemailEnabled":true,"phoneNumbers":[{"answerConfirmationRequiredEnabled":"...","numberOfRings":"...","phoneNumber":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SEQUENTIAL_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_SEQUENTIAL_RING = '{"callsFrom":"SELECT_PHONE_NUMBERS","ringEnabled":true,"scheduleName":"...","scheduleType":"holidays","scheduleLevel":"GROUP","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("create-criteria-sequential-ring", short_help="Add User Sequential Ring Criteria.")
def create_criteria_sequential_ring(
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the location's schedule which determines when the sequential ring is in effect."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: holidays, businessHours"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: SELECT_PHONE_NUMBERS, ANY_PHONE_NUMBER"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true` incoming calls from private numbers are allowed. This is only applicable when `callsFrom` is set to `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true` incoming calls from unavailable numbers are allowed. This is only applicable when `callsFrom` is set to `SELECT_PHONE_NUMBERS`."),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="(required) When set to `true` sequential ringing is enabled for calls that meet the current criteria. Criteria with `ringEnabled` set to `false` take priority."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add User Sequential Ring Criteria.\n\n\b\nExample: wxcli my-call-settings create-criteria-sequential-ring --calls-from SELECT_PHONE_NUMBERS --ring-enabled\n\n\b\nExample --json-body: '{"callsFrom":"SELECT_PHONE_NUMBERS","ringEnabled":true,"scheduleName":"...","scheduleType":"holidays","scheduleLevel":"GROUP","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SEQUENTIAL_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing/criteria"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-criteria-sequential-ring", short_help="Get Sequential Ring Criteria Settings for User.")
def show_criteria_sequential_ring(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Sequential Ring Criteria Settings for User.\n\n\b\nExample: wxcli my-call-settings show-criteria-sequential-ring ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SEQUENTIAL_RING = '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'

@app.command("update-criteria-sequential-ring", short_help="Modify Sequential Ring Criteria Settings for User.")
def update_criteria_sequential_ring(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule to be associated with the criteria."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, LOCATION"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, means this criteria applies for anonymous callers. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, means this criteria applies for unavailable callers. Required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="Determines whether sequential ring is applied for calls matching this criteria. If `true`, sequential ring is applied. Criteria with ringEnabled set to false have precedence over criteria with ringEnabled set to true."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Sequential Ring Criteria Settings for User.\n\n\b\nExample: wxcli my-call-settings update-criteria-sequential-ring ID\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SEQUENTIAL_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing/criteria/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-sequential-ring", short_help="Delete Sequential Ring Criteria.")
def delete_criteria_sequential_ring(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Sequential Ring Criteria.\n\n\b\nExample: wxcli my-call-settings delete-criteria-sequential-ring ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing/criteria/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-simultaneous-ring", short_help="Retrieve My Simultaneous Ring Settings.")
def list_simultaneous_ring(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Answer Confirmation Required Enabled', 'answerConfirmationRequiredEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SIMULTANEOUS_RING = '{"enabled":true,"doNotRingIfOnCallEnabled":true,"phoneNumbers":[{"phoneNumber":"...","answerConfirmationEnabled":"..."}],"criteriasEnabled":true}'

@app.command("update-simultaneous-ring", short_help="Modify My Simultaneous Ring Settings.")
def update_simultaneous_ring(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Simultaneous Ring is enabled or not."),
    do_not_ring_if_on_call_enabled: bool = typer.Option(None, "--do-not-ring-if-on-call-enabled/--no-do-not-ring-if-on-call-enabled", help="When set to `true`, the configured phone numbers won't ring when you are on a call."),
    criterias_enabled: bool = typer.Option(None, "--criterias-enabled/--no-criterias-enabled", help="Controls whether the criteria for simultaneous ring are enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Simultaneous Ring Settings.\n\n\b\nExample --json-body: '{"enabled":true,"doNotRingIfOnCallEnabled":true,"phoneNumbers":[{"phoneNumber":"...","answerConfirmationEnabled":"..."}],"criteriasEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SIMULTANEOUS_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-criteria-simultaneous-ring", short_help="Retrieve My Simultaneous Ring Criteria.")
def show_criteria_simultaneous_ring(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve My Simultaneous Ring Criteria.\n\n\b\nExample: wxcli my-call-settings show-criteria-simultaneous-ring ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing/criteria/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CRITERIA_SIMULTANEOUS_RING = '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'

@app.command("update-criteria-simultaneous-ring", short_help="Modify My Simultaneous Ring Criteria.")
def update_criteria_simultaneous_ring(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule which determines when the simultaneous ring is in effect."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, the criteria applies to calls from anonymous callers. Value for this attribute is required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, the criteria applies to calls from unavailable callers. Value for this attribute is required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="When set to `true` simultaneous ringing is enabled for calls that meet this criteria. Criteria with `ringEnabled` set to `false` take priority."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Simultaneous Ring Criteria.\n\n\b\nExample: wxcli my-call-settings update-criteria-simultaneous-ring ID\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CRITERIA_SIMULTANEOUS_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing/criteria/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete-criteria-simultaneous-ring", short_help="Delete My Simultaneous Ring Criteria.")
def delete_criteria_simultaneous_ring(
    id: str = typer.Argument(help="Webex CRITERIA id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete My Simultaneous Ring Criteria.\n\n\b\nExample: wxcli my-call-settings delete-criteria-simultaneous-ring ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing/criteria/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_CRITERIA_SIMULTANEOUS_RING = '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","ringEnabled":true,"anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'

@app.command("create-criteria-simultaneous-ring", short_help="Create My Simultaneous Ring Criteria.")
def create_criteria_simultaneous_ring(
    schedule_name: str = typer.Option(None, "--schedule-name", help="(required) Name of the schedule which determines when the simultaneous ring is in effect."),
    schedule_type: str = typer.Option(None, "--schedule-type", help="(required) Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="(required) Choices: PEOPLE, GROUP"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, the criteria applies to calls from anonymous callers. Value for this attribute is required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, the criteria applies to calls from unavailable callers. Value for this attribute is required if `callsFrom` is `SELECT_PHONE_NUMBERS`."),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="(required) When set to `true` simultaneous ringing is enabled for calls that meet this criteria. Criteria with `ringEnabled` set to `false` take priority."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create My Simultaneous Ring Criteria.\n\n\b\nExample: wxcli my-call-settings create-criteria-simultaneous-ring --schedule-name SCHEDULE_NAME --schedule-type businessHours --schedule-level PEOPLE --calls-from ANY_PHONE_NUMBER --ring-enabled\n\n\b\nExample --json-body: '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"PEOPLE","callsFrom":"ANY_PHONE_NUMBER","ringEnabled":true,"anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CRITERIA_SIMULTANEOUS_RING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing/criteria"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("list-numbers", short_help="Retrieve My Guest Calling Numbers.")
def list_numbers(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber')], limit=limit)



@app.command("list-speed-dials", short_help="Get Speed Dials.")
def list_speed_dials(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Speed Dials."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/speedDials"
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
    items = result.get("speedDials", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Last Name', 'lastName'), ('First Name', 'firstName'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_UPDATE_SPEED_DIALS = '{"speedDials":[{"id":"...","phoneNumber":"...","lineKeyLabel":"..."}]}'

@app.command("update-speed-dials", short_help="Modify Speed Dials.")
def update_speed_dials(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Speed Dials.\n\n\b\nExample --json-body: '{"speedDials":[{"id":"...","phoneNumber":"...","lineKeyLabel":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SPEED_DIALS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/speedDials"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("list-available-members", short_help="Get Speed Dial Available Members.")
def list_available_members(
    location_id: str = typer.Option(None, "--location-id", help="Return the members list available in this location."),
    name: str = typer.Option(None, "--name", help="Search (Contains) based on first name and last name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number and extension."),
    order: str = typer.Option(None, "--order", help="Sort by first name (`firstName`) or last name (`lastName`). Sort directions asc or desc. * `asc` - Sort in ascending order. * `desc` - Sort in descending order."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Speed Dial Available Members."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/speedDials/availableMembers"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
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
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Last Name', 'lastName'), ('First Name', 'firstName'), ('Phone Number', 'phoneNumber')], limit=limit)



@app.command("list-organization", short_help="Get Location List for My Organization.")
def list_organization(
    name: str = typer.Option(None, "--name", help="Search (Contains) based on location name. Multiple values are logically OR-ed."),
    order: str = typer.Option(None, "--order", help="Sort by location name (`name`). Sort directions asc or desc. * `asc` - Sort in ascending order. * `desc` - Sort in descending order."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location List for My Organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/organization/locations"
    params = {}
    if name is not None:
        params["name"] = name
    if order is not None:
        params["order"] = order
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
    items = result.get("locations", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Routing Prefix', 'routingPrefix')], limit=limit)



@app.command("show-large-org-status", short_help="Get Large Organization Status.")
def show_large_org_status(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Large Organization Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/organization/largeOrgStatus"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


