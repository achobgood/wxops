import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling conference-controls.")


@app.command("create")
def create(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Start Conference."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



@app.command("delete")
def delete(
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Release Conference."""
    if not force:
        typer.confirm(f"Delete {item}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {item}")



@app.command("list")
def cmd_list(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Conference Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
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
    items = result.get("conference", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-add-participant")
def create_add_participant(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add Participant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference/addParticipant"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



@app.command("create-mute")
def create_mute(
    call_id: str = typer.Option(None, "--call-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mute."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference/mute"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
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



@app.command("create-unmute")
def create_unmute(
    call_id: str = typer.Option(None, "--call-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unmute."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference/unmute"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
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



@app.command("create-deafen")
def create_deafen(
    call_id: str = typer.Option(None, "--call-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Deafen Participant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference/deafen"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
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



@app.command("create-undeafen")
def create_undeafen(
    call_id: str = typer.Option(None, "--call-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Undeafen Participant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference/undeafen"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
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



@app.command("create-hold")
def create_hold(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hold."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference/hold"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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



@app.command("create-resume")
def create_resume(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/conference/resume"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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


