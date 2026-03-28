import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling agents.")


@app.command("update")
def update(
    agent_id: str = typer.Option(None, "--agent-id", help=""),
    logout_reason: str = typer.Option(None, "--logout-reason", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Logout."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/agents/logout"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_id is not None:
            body["agentId"] = agent_id
        if logout_reason is not None:
            body["logoutReason"] = logout_reason
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("update-state-session")
def update_state_session(
    agent_id: str = typer.Option(None, "--agent-id", help=""),
    state: str = typer.Option(None, "--state", help=""),
    aux_code_id: str = typer.Option(None, "--aux-code-id", help=""),
    last_state_change_reason: str = typer.Option(None, "--last-state-change-reason", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """State Change."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/agents/session/state"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_id is not None:
            body["agentId"] = agent_id
        if state is not None:
            body["state"] = state
        if aux_code_id is not None:
            body["auxCodeId"] = aux_code_id
        if last_state_change_reason is not None:
            body["lastStateChangeReason"] = last_state_change_reason
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create")
def create(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reload."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/agents/reload"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-buddy-list")
def create_buddy_list(
    media_type: str = typer.Option(None, "--media-type", help=""),
    agent_profile_id: str = typer.Option(None, "--agent-profile-id", help=""),
    state: str = typer.Option(None, "--state", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Buddy Agents List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/agents/buddyList"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if media_type is not None:
            body["mediaType"] = media_type
        if agent_profile_id is not None:
            body["agentProfileId"] = agent_profile_id
        if state is not None:
            body["state"] = state
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list")
def cmd_list(
    agent_ids: str = typer.Option(None, "--agent-ids", help="Filter agent activities by agent ids separated with commas i"),
    team_ids: str = typer.Option(None, "--team-ids", help="Filter agent activities by team ids separated with commas if"),
    channel_types: str = typer.Option(None, "--channel-types", help="Channel type(s) permitted in response. Separate values with"),
    from_param: str = typer.Option(None, "--from", help="Filter agent activities created after given epoch timestamp"),
    to: str = typer.Option(None, "--to", help="Filter agent activities created before given epoch timestamp"),
    page_size: str = typer.Option(None, "--page-size", help="Maximum page size in response. Maximum allowed value is 1000"),
    page: str = typer.Option(None, "--page", help="Page number to be passed. Maximum number of records that can"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Agent Activities."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/agents/activities"
    params = {}
    if agent_ids is not None:
        params["agentIds"] = agent_ids
    if team_ids is not None:
        params["teamIds"] = team_ids
    if channel_types is not None:
        params["channelTypes"] = channel_types
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if page_size is not None:
        params["pageSize"] = page_size
    if page is not None:
        params["page"] = page
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("data", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-statistics")
def list_statistics(
    from_param: str = typer.Option(None, "--from", help="Start time for the query (in epoch milliseconds). Any epoch"),
    to: str = typer.Option(None, "--to", help="End time for the query (in epoch milliseconds). Any epoch ti"),
    interval: str = typer.Option(None, "--interval", help="Time interval (in minutes) to chunk statistics by i.e. break"),
    agent_ids: str = typer.Option(None, "--agent-ids", help="Comma-separated list of agent IDs. A maximum of 100 values i"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Agent Statistics."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/agents/statistics"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if interval is not None:
        params["interval"] = interval
    if agent_ids is not None:
        params["agentIds"] = agent_ids
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("data", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-state-session-1")
def update_state_session_1(
    agent_id: str = typer.Option(None, "--agent-id", help=""),
    state: str = typer.Option(None, "--state", help=""),
    aux_code_id: str = typer.Option(None, "--aux-code-id", help=""),
    reason: str = typer.Option(None, "--reason", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """State Change\n\nExample --json-body:\n  '{"channelType":["..."],"agentId":"...","state":"...","auxCodeId":"...","reason":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/v2/agents/session/state"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_id is not None:
            body["agentId"] = agent_id
        if state is not None:
            body["state"] = state
        if aux_code_id is not None:
            body["auxCodeId"] = aux_code_id
        if reason is not None:
            body["reason"] = reason
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create-login-agents")
def create_login_agents(
    team_id: str = typer.Option(None, "--team-id", help=""),
    dial_number: str = typer.Option(None, "--dial-number", help=""),
    is_extension: str = typer.Option(None, "--is-extension", help=""),
    device_id: str = typer.Option(None, "--device-id", help=""),
    device_type: str = typer.Option(None, "--device-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Login\n\nExample --json-body:\n  '{"teamId":"...","dialNumber":"...","isExtension":"...","roles":["..."],"deviceId":"...","deviceType":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/v2/agents/login"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if team_id is not None:
            body["teamId"] = team_id
        if dial_number is not None:
            body["dialNumber"] = dial_number
        if is_extension is not None:
            body["isExtension"] = is_extension
        if device_id is not None:
            body["deviceId"] = device_id
        if device_type is not None:
            body["deviceType"] = device_type
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("update-logout")
def update_logout(
    agent_id: str = typer.Option(None, "--agent-id", help=""),
    logout_reason: str = typer.Option(None, "--logout-reason", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Logout."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/v2/agents/logout"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_id is not None:
            body["agentId"] = agent_id
        if logout_reason is not None:
            body["logoutReason"] = logout_reason
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create-reload")
def create_reload(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reload."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/v2/agents/reload"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-login-agents-1")
def create_login_agents_1(
    team_id: str = typer.Option(None, "--team-id", help=""),
    dial_number: str = typer.Option(None, "--dial-number", help=""),
    is_extension: str = typer.Option(None, "--is-extension", help=""),
    device_id: str = typer.Option(None, "--device-id", help=""),
    device_type: str = typer.Option(None, "--device-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Login\n\nExample --json-body:\n  '{"teamId":"...","dialNumber":"...","isExtension":"...","roles":["..."],"deviceId":"...","deviceType":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/agents/login"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if team_id is not None:
            body["teamId"] = team_id
        if dial_number is not None:
            body["dialNumber"] = dial_number
        if is_extension is not None:
            body["isExtension"] = is_extension
        if device_id is not None:
            body["deviceId"] = device_id
        if device_type is not None:
            body["deviceType"] = device_type
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


