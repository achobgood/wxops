import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling caller-reputation-provider.")


@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Caller Reputation Provider Service Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider"
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



@app.command("update")
def update(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    name: str = typer.Option(None, "--name", help=""),
    client_id: str = typer.Option(None, "--client-id", help=""),
    client_secret: str = typer.Option(None, "--client-secret", help=""),
    call_block_score_threshold: str = typer.Option(None, "--call-block-score-threshold", help=""),
    call_allow_score_threshold: str = typer.Option(None, "--call-allow-score-threshold", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Caller Reputation Provider Service Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider"
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Caller Reputation Provider Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider/status"
    params = {}
    if organization_id is not None:
        params["organizationId"] = organization_id
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
    items = result.get("status", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("unlock-caller-reputation")
def unlock_caller_reputation(
    id_param: str = typer.Option(None, "--id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unlock Caller Reputation Provider."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/serviceSettings/callerReputationProvider/actions/unlock/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
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



@app.command("list-providers")
def list_providers(
    organization_id: str = typer.Option(None, "--organization-id", help="Unique identifier for the organization."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("providers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


