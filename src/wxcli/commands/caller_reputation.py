import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling caller-reputation.")


@app.command("show")
def show(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Indicates if the caller reputation provider service is enabl"),
    id_param: str = typer.Option(None, "--id", help="Unique identifier for the reputation provider."),
    name: str = typer.Option(None, "--name", help="Name of the reputation provider."),
    client_id: str = typer.Option(None, "--client-id", help="Client ID used for integration with the reputation provider."),
    client_secret: str = typer.Option(None, "--client-secret", help="Client secret used for integration with the reputation provi"),
    call_block_score_threshold: str = typer.Option(None, "--call-block-score-threshold", help="Score threshold for blocking calls."),
    call_allow_score_threshold: str = typer.Option(None, "--call-allow-score-threshold", help="Score threshold for allowing calls."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Caller Reputation Provider Service Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider"
    params = {}
    if organization_id is not None:
        params["organizationId"] = organization_id
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("show-status")
def show_status(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("unlock-caller-reputation")
def unlock_caller_reputation(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    id_param: str = typer.Option(None, "--id", help="Unique identifier for the reputation provider."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unlock Caller Reputation Provider."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider/actions/unlock/invoke"
    params = {}
    if organization_id is not None:
        params["organizationId"] = organization_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    print_json(result)



@app.command("list")
def cmd_list(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("providers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


