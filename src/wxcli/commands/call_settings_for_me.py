import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling call-settings-for-me.")


@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Personal Assistant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/personalAssistant"
    params = {}
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
    items = result.get("personalAssistant", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update")
def update(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    presence: str = typer.Option(None, "--presence", help="e.g. GONE_FOR_THE_DAY"),
    until_date_time: str = typer.Option(None, "--until-date-time", help=""),
    transfer_enabled: bool = typer.Option(None, "--transfer-enabled/--no-transfer-enabled", help=""),
    transfer_number: str = typer.Option(None, "--transfer-number", help=""),
    alerting: str = typer.Option(None, "--alerting", help="e.g. PLAY_RING_REMINDER"),
    alert_me_first_number_of_rings: str = typer.Option(None, "--alert-me-first-number-of-rings", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Personal Assistant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/personalAssistant"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if presence is not None:
            body["presence"] = presence
        if until_date_time is not None:
            body["untilDateTime"] = until_date_time
        if transfer_enabled is not None:
            body["transferEnabled"] = transfer_enabled
        if transfer_number is not None:
            body["transferNumber"] = transfer_number
        if alerting is not None:
            body["alerting"] = alerting
        if alert_me_first_number_of_rings is not None:
            body["alertMeFirstNumberOfRings"] = alert_me_first_number_of_rings
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



@app.command("list-available-preferred-answer-endpoints-settings")
def list_available_preferred_answer_endpoints_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("availablePreferredAnswerEndpoints", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-preferred-answer-endpoints-secondary-lines")
def list_available_preferred_answer_endpoints_secondary_lines(
    line_owner_id: str = typer.Argument(help="lineOwnerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("availablePreferredAnswerEndpoints", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-preferred-answer-endpoint-settings")
def list_preferred_answer_endpoint_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/preferredAnswerEndpoint"
    params = {}
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
    items = result.get("preferredAnswerEndpoint", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-preferred-answer-endpoint-settings")
def update_preferred_answer_endpoint_settings(
    preferred_answer_endpoint_id: str = typer.Option(None, "--preferred-answer-endpoint-id", help=""),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-preferred-answer-endpoint-secondary-lines")
def list_preferred_answer_endpoint_secondary_lines(
    line_owner_id: str = typer.Argument(help="lineOwnerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Preferred Answer Endpoint."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{line_owner_id}/preferredAnswerEndpoint"
    params = {}
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
    items = result.get("preferredAnswerEndpoint", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-preferred-answer-endpoint-secondary-lines")
def update_preferred_answer_endpoint_secondary_lines(
    line_owner_id: str = typer.Argument(help="lineOwnerId"),
    preferred_answer_endpoint_id: str = typer.Option(None, "--preferred-answer-endpoint-id", help=""),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My WebexGoOverride Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/webexGoOverride"
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



@app.command("update-webex-go-override")
def update_webex_go_override(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-caller-id-settings")
def update_caller_id_settings(
    calling_line_id_delivery_blocking_enabled: bool = typer.Option(None, "--calling-line-id-delivery-blocking-enabled/--no-calling-line-id-delivery-blocking-enabled", help=""),
    connected_line_identification_restriction_enabled: bool = typer.Option(None, "--connected-line-identification-restriction-enabled/--no-connected-line-identification-restriction-enabled", help=""),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-caller-id-secondary-lines")
def update_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    calling_line_id_delivery_blocking_enabled: bool = typer.Option(None, "--calling-line-id-delivery-blocking-enabled/--no-calling-line-id-delivery-blocking-enabled", help=""),
    connected_line_identification_restriction_enabled: bool = typer.Option(None, "--connected-line-identification-restriction-enabled/--no-connected-line-identification-restriction-enabled", help=""),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-selected-caller-id-settings")
def update_selected_caller_id_settings(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure My Selected Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/selectedCallerId"
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-selected-caller-id-secondary-lines")
def update_selected_caller_id_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Selected Caller ID Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/selectedCallerId"
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



@app.command("list-available-caller-ids-settings")
def list_available_caller_ids_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("availableCallerIds", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-caller-ids-secondary-lines")
def list_available_caller_ids_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("availableCallerIds", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-endpoints")
def list_endpoints(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("endpoints", result if isinstance(result, list) else [])
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-endpoints")
def update_endpoints(
    endpoint_id: str = typer.Argument(help="endpointId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Endpoints Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/endpoints/{endpoint_id}"
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("list-me")
def list_me(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Own Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me"
    params = {}
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
    items = result.get("me", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-feature-access-code-settings")
def list_feature_access_code_settings(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("featureAccessCode", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-feature-access-code-secondary-lines")
def list_feature_access_code_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("featureAccessCode", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-assigned-assistants")
def list_assigned_assistants(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("assignedAssistants", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-assigned-assistants")
def update_assigned_assistants(
    allow_opt_in_out_enabled: bool = typer.Option(None, "--allow-opt-in-out-enabled/--no-allow-opt-in-out-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Executive Assigned Assistants."""
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-available-assistants")
def list_available_assistants(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("availableAssistants", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-assistant")
def show_assistant(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Executive Assistant Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/executive/assistant"
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



@app.command("update-assistant")
def update_assistant(
    forward_filtered_calls_enabled: bool = typer.Option(None, "--forward-filtered-calls-enabled/--no-forward-filtered-calls-enabled", help=""),
    forward_to_phone_number: str = typer.Option(None, "--forward-to-phone-number", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Executive Assistant Settings."""
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-services-settings")
def show_services_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Calling Services List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/services"
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



@app.command("show-services-secondary-lines")
def show_services_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Calling Services List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/services"
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



@app.command("show-single-number-reach")
def show_single_number_reach(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User's Single Number Reach Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach"
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



@app.command("update-single-number-reach")
def update_single_number_reach(
    alert_all_locations_for_click_to_dial_calls_enabled: bool = typer.Option(None, "--alert-all-locations-for-click-to-dial-calls-enabled/--no-alert-all-locations-for-click-to-dial-calls-enabled", help=""),
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
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    name: str = typer.Option(None, "--name", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    do_not_forward_calls_enabled: bool = typer.Option(None, "--do-not-forward-calls-enabled/--no-do-not-forward-calls-enabled", help=""),
    answer_confirmation_enabled: bool = typer.Option(None, "--answer-confirmation-enabled/--no-answer-confirmation-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
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



@app.command("update-numbers")
def update_numbers(
    phone_number_id: str = typer.Argument(help="phoneNumberId"),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    name: str = typer.Option(None, "--name", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    do_not_forward_calls_enabled: bool = typer.Option(None, "--do-not-forward-calls-enabled/--no-do-not-forward-calls-enabled", help=""),
    answer_confirmation_enabled: bool = typer.Option(None, "--answer-confirmation-enabled/--no-answer-confirmation-enabled", help=""),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-call-forwarding-settings")
def update_call_forwarding_settings(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure My Call Forwarding Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callForwarding"
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-call-forwarding-secondary-lines")
def update_call_forwarding_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Call Forwarding Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callForwarding"
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



@app.command("show-call-pickup-group-settings")
def show_call_pickup_group_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Pickup Group Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callPickupGroup"
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



@app.command("show-call-pickup-group-secondary-lines")
def show_call_pickup_group_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Call Pickup Group Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callPickupGroup"
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



@app.command("show-call-park-settings")
def show_call_park_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Park Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callPark"
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



@app.command("show-call-park-secondary-lines")
def show_call_park_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner Call Park Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/callPark"
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



@app.command("update-voicemail-settings")
def update_voicemail_settings(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Configure Voicemail Settings for a Person."""
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-voicemail-secondary-lines")
def update_voicemail_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Voicemail Settings."""
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("show-call-block")
def show_call_block(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Block Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/callBlock"
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



@app.command("create-numbers")
def create_numbers(
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {phone_number_id}")



@app.command("show-monitoring")
def show_monitoring(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Monitoring Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/monitoring"
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



@app.command("show-queues-settings")
def show_queues_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Call Center Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/queues"
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



@app.command("update-queues-settings")
def update_queues_settings(
    agent_a_c_d_state: str = typer.Option(None, "--agent-a-c-d-state", help="e.g. UNAVAILABLE"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Call Center Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/queues"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_a_c_d_state is not None:
            body["agentACDState"] = agent_a_c_d_state
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



@app.command("show-queues-secondary-lines")
def show_queues_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Secondary Line Owner's Call Center Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/queues"
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



@app.command("update-queues-secondary-lines")
def update_queues_secondary_lines(
    lineowner_id: str = typer.Argument(help="lineownerId"),
    agent_a_c_d_state: str = typer.Option(None, "--agent-a-c-d-state", help="e.g. UNAVAILABLE"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify My Secondary Line Owner's Call Center Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineowner_id}/queues"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_a_c_d_state is not None:
            body["agentACDState"] = agent_a_c_d_state
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)


