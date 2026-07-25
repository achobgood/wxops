import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling caller-reputation.")


@app.command("show")
def show(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Caller Reputation Provider Service Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider"
    params = {}
    if organization_id is not None:
        params["organizationId"] = organization_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"enabled":true,"id":"...","name":"...","clientId":"...","clientSecret":"...","callBlockScoreThreshold":"...","callAllowScoreThreshold":"..."}'

@app.command("update")
def update(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Indicates if the caller reputation provider service is enabled. when set to true, all other fields are required except clientSecret."),
    id_param: str = typer.Option(None, "--id", help="Unique identifier for the reputation provider."),
    name: str = typer.Option(None, "--name", help="Name of the reputation provider."),
    client_id: str = typer.Option(None, "--client-id", help="Client ID used for integration with the reputation provider."),
    client_secret: str = typer.Option(None, "--client-secret", help="Client secret used for integration with the reputation provider."),
    call_block_score_threshold: str = typer.Option(None, "--call-block-score-threshold", help="Score threshold for blocking calls."),
    call_allow_score_threshold: str = typer.Option(None, "--call-allow-score-threshold", help="Score threshold for allowing calls."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Caller Reputation Provider Service Settings\n\nExample --json-body:\n  '{"enabled":true,"id":"...","name":"...","clientId":"...","clientSecret":"...","callBlockScoreThreshold":"...","callAllowScoreThreshold":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider"
    params = {}
    if organization_id is not None:
        params["organizationId"] = organization_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if id_param is not None:
            body["id"] = id_param
        if name is not None:
            body["name"] = name
        if client_id is not None:
            body["clientId"] = client_id
        if client_secret is not None:
            body["clientSecret"] = client_secret
        if call_block_score_threshold is not None:
            body["callBlockScoreThreshold"] = call_block_score_threshold
        if call_allow_score_threshold is not None:
            body["callAllowScoreThreshold"] = call_allow_score_threshold
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-status")
def show_status(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Caller Reputation Provider Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider/status"
    params = {}
    if organization_id is not None:
        params["organizationId"] = organization_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UNLOCK_CALLER_REPUTATION = '{"id":"..."}'

@app.command("unlock-caller-reputation")
def unlock_caller_reputation(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    id_param: str = typer.Option(None, "--id", help="Unique identifier for the reputation provider."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unlock Caller Reputation Provider\n\nExample --json-body:\n  '{"id":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UNLOCK_CALLER_REPUTATION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider/actions/unlock/invoke"
    params = {}
    if organization_id is not None:
        params["organizationId"] = organization_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list")
def cmd_list(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Caller Reputation Provider Providers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider/providers"
    params = {}
    if organization_id is not None:
        params["organizationId"] = organization_id
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
    items = result.get("providers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


