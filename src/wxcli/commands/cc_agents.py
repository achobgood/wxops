import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-agents.")


_BODY_SKELETON_CREATE = '{"dialNumber":"...","roles":["..."],"teamId":"...","isExtension":true,"deviceType":"...","deviceId":"..."}'

@app.command("create", short_help="Login.")
def create(
    dial_number: str = typer.Option(None, "--dial-number", help="(required) A dialNumber field contains the number to dial such as a route point or extension, maximum length 43 characters."),
    team_id: str = typer.Option(None, "--team-id", help="The unique ID representing a team of users. Leaving this field blank is valid for supervisor role but invalid for agent role, maximum length 36 characters."),
    is_extension: bool = typer.Option(None, "--is-extension/--no-is-extension", help="It indicates if the dialNumber field is full number or extension. It is set to false by default."),
    device_type: str = typer.Option(None, "--device-type", help="It represents the way to differentiate type of login request (```AGENT_DN```, ```EXTENSION```, ```BROWSER```). Leaving this field is valid for supervisor role but invalid for agent role."),
    device_id: str = typer.Option(None, "--device-id", help="It is equal to dialNumber for AGENT_DN & EXTENSION deviceType and for BROWSER it is populated as webrtc-AgentUUID, maximum length 43 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Login.\n\n\b\nExample: wxcli cc-agents create --json-body '{"dialNumber":"...","roles":["..."]}'\n\n\b\nExample --json-body: '{"dialNumber":"...","roles":["..."],"teamId":"...","isExtension":true,"deviceType":"...","deviceId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agents/login"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if dial_number is not None:
            body["dialNumber"] = dial_number
        if team_id is not None:
            body["teamId"] = team_id
        if is_extension is not None:
            body["isExtension"] = is_extension
        if device_type is not None:
            body["deviceType"] = device_type
        if device_id is not None:
            body["deviceId"] = device_id
        _missing = [f for f in ['dialNumber'] if f not in body or body[f] is None]
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



_BODY_SKELETON_UPDATE = '{"logoutReason":"...","agentId":"..."}'

@app.command("update", short_help="Logout.")
def update(
    logout_reason: str = typer.Option(None, "--logout-reason", help="The reason for performing logout operation, maximum length 128 characters."),
    agent_id: str = typer.Option(None, "--agent-id", help="Unique ID of the user who is being logged out, maximum length 36 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Logout.\n\n\b\nExample: wxcli cc-agents update --logout-reason LOGOUT_REASON\n\n\b\nExample --json-body: '{"logoutReason":"...","agentId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agents/logout"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if logout_reason is not None:
            body["logoutReason"] = logout_reason
        if agent_id is not None:
            body["agentId"] = agent_id
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



_BODY_SKELETON_UPDATE_STATE_SESSION = '{"state":"...","auxCodeId":"...","lastStateChangeReason":"...","agentId":"..."}'

@app.command("update-state-session", short_help="State Change.")
def update_state_session(
    state: str = typer.Option(None, "--state", help="It represents the current state of the user. Can be set to ```Available``` or ```Idle```."),
    aux_code_id: str = typer.Option(None, "--aux-code-id", help="Auxiliary Codes are status codes which an agent can select in Webex Contact Center Agent Desktop. They are of two types: ```Idle``` and ```Wrap-Up``` codes, and every agent profile must have one of each for the agent to use. Idle codes are used to explain an agent's unavailability to take customer..."),
    last_state_change_reason: str = typer.Option(None, "--last-state-change-reason", help="It represents the reason of the last state change request, maximum length 128 characters."),
    agent_id: str = typer.Option(None, "--agent-id", help="User for which state change is initiated, maximum length 36 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """State Change.\n\n\b\nExample: wxcli cc-agents update-state-session --state STATE --aux-code-id AUX_CODE_ID\n\n\b\nExample --json-body: '{"state":"...","auxCodeId":"...","lastStateChangeReason":"...","agentId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_STATE_SESSION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agents/session/state"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if state is not None:
            body["state"] = state
        if aux_code_id is not None:
            body["auxCodeId"] = aux_code_id
        if last_state_change_reason is not None:
            body["lastStateChangeReason"] = last_state_change_reason
        if agent_id is not None:
            body["agentId"] = agent_id
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



@app.command("create-reload-agents", short_help="Reload.")
def create_reload_agents(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reload."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agents/reload"
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
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_BUDDY_LIST = '{"agentProfileId":"...","mediaType":"...","state":"..."}'

@app.command("create-buddy-list", short_help="Buddy Agents List.")
def create_buddy_list(
    agent_profile_id: str = typer.Option(None, "--agent-profile-id", help="(required) The profile ID of a particular agent. Can be obtained from [Users API](/docs/users), maximum length 36 characters."),
    media_type: str = typer.Option(None, "--media-type", help="(required) The media type for the request. The supported values are ```telephony```, ```chat```, ```social```, ```email```, ```workItem``` and ```customMessaging```."),
    state: str = typer.Option(None, "--state", help="It represents the current state of the returned agents which can be either ```Available``` or ```Idle```. If state is omitted from the payload, the API will return a list of both available and idle agents. This is useful for consult scenarios, since consulting an idle agent is also supported."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Buddy Agents List.\n\n\b\nExample: wxcli cc-agents create-buddy-list --agent-profile-id AGENT_PROFILE_ID --media-type MEDIA_TYPE\n\n\b\nExample --json-body: '{"agentProfileId":"...","mediaType":"...","state":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BUDDY_LIST), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agents/buddyList"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if agent_profile_id is not None:
            body["agentProfileId"] = agent_profile_id
        if media_type is not None:
            body["mediaType"] = media_type
        if state is not None:
            body["state"] = state
        _missing = [f for f in ['agentProfileId', 'mediaType'] if f not in body or body[f] is None]
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



@app.command("list", hidden=True)
@app.command("list-activities", short_help="Get Agent Activities.")
def list_activities(
    agent_ids: str = typer.Option(None, "--agent-ids", help="Filter agent activities by agent ids separated with commas if more than one value (max 100). By default, there is no agent filtering."),
    team_ids: str = typer.Option(None, "--team-ids", help="Filter agent activities by team ids separated with commas if more than one value (max 100). By default, there is no team filtering."),
    channel_types: str = typer.Option(None, "--channel-types", help="Channel type(s) permitted in response. Separate values with commas. Must be lowercase. By default, there is no channelType filtering."),
    from_param: str = typer.Option(..., "--from", help="Filter agent activities created after given epoch timestamp in UTC (in milliseconds)."),
    to: str = typer.Option(None, "--to", help="Filter agent activities created before given epoch timestamp in UTC (in milliseconds). If unspecified, queries up to the present. The difference between to and from timestamps must be less than 24 hours (86400000 milli seconds)"),
    page_size: str = typer.Option(None, "--page-size", help="Maximum page size in response. Maximum allowed value is 1000. Defaults to 100 items per page."),
    page: str = typer.Option(None, "--page", help="Page number to be passed. Maximum number of records that can be fetched for the given from and to is 10,000. So maximum page number allowed is based on it. Defaults to 0."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Agent Activities.\n\n\b\nExample: wxcli cc-agents list-activities --from FROM_PARAM"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agents/activities"
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
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Agent ID', 'agentId'), ('Agent Name', 'agentName'), ('Active', 'active'), ('Agent DN', 'agentDn'), ('Agent Login', 'agentLogin')], limit=limit)



@app.command("list-statistics", short_help="Get Agent Statistics.")
def list_statistics(
    from_param: str = typer.Option(..., "--from", help="Start time for the query (in epoch milliseconds). Any epoch time can be passed in the input, from date will be rounded down to nearest 15 minute window. For example, epoch time of 12:05 will be rounded down to 12:00."),
    to: str = typer.Option(..., "--to", help="End time for the query (in epoch milliseconds). Any epoch time can be passed in the input, from date will be rounded down to nearest 15 minute window. For example, epoch time of 12:55 will be rounded down to 12:45. The difference between to and from time must be less than 24 hours (86400000..."),
    interval: str = typer.Option(None, "--interval", help="Time interval (in minutes) to chunk statistics by i.e. break up the entire from-to timeframe by this interval amount so that statistics can be viewed incrementally. Supported values are 15, 30, or 60."),
    agent_ids: str = typer.Option(None, "--agent-ids", help="Comma-separated list of agent IDs. A maximum of 100 values is permitted. If values are not provided, all agents of an organization are returned."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Agent Statistics.\n\n\b\nExample: wxcli cc-agents list-statistics --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agents/statistics"
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Agent ID', 'agentId'), ('Agent Name', 'agentName'), ('Interval Start Time', 'intervalStartTime'), ('Team ID', 'teamId'), ('Team Name', 'teamName')], limit=limit)



_BODY_SKELETON_CREATE_LOGIN = '{"dialNumber":"...","roles":["..."],"teamId":"...","isExtension":true,"deviceType":"...","deviceId":"..."}'

@app.command("create-login", short_help="Login.")
def create_login(
    dial_number: str = typer.Option(None, "--dial-number", help="(required) A dialNumber field contains the number to dial such as a route point or extension, maximum length 43 characters."),
    team_id: str = typer.Option(None, "--team-id", help="The unique ID representing a team of users. Leaving this field blank is valid for supervisor role but invalid for agent role, maximum length 36 characters."),
    is_extension: bool = typer.Option(None, "--is-extension/--no-is-extension", help="It indicates if the dialNumber field is full number or extension. It is set to false by default."),
    device_type: str = typer.Option(None, "--device-type", help="It represents the way to differentiate type of login request (```AGENT_DN```, ```EXTENSION```, ```BROWSER```). Leaving this field is valid for supervisor role but invalid for agent role."),
    device_id: str = typer.Option(None, "--device-id", help="It is equal to dialNumber for AGENT_DN & EXTENSION deviceType and for BROWSER it is populated as webrtc-AgentUUID, maximum length 43 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Login.\n\n\b\nExample: wxcli cc-agents create-login --json-body '{"dialNumber":"...","roles":["..."]}'\n\n\b\nExample --json-body: '{"dialNumber":"...","roles":["..."],"teamId":"...","isExtension":true,"deviceType":"...","deviceId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_LOGIN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/agents/login"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if dial_number is not None:
            body["dialNumber"] = dial_number
        if team_id is not None:
            body["teamId"] = team_id
        if is_extension is not None:
            body["isExtension"] = is_extension
        if device_type is not None:
            body["deviceType"] = device_type
        if device_id is not None:
            body["deviceId"] = device_id
        _missing = [f for f in ['dialNumber'] if f not in body or body[f] is None]
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



_BODY_SKELETON_UPDATE_LOGOUT = '{"logoutReason":"...","agentId":"..."}'

@app.command("update-logout", short_help="Logout.")
def update_logout(
    logout_reason: str = typer.Option(None, "--logout-reason", help="The reason for performing logout operation, maximum length 128 characters."),
    agent_id: str = typer.Option(None, "--agent-id", help="Unique ID of the user who is being logged out, maximum length 36 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Logout.\n\n\b\nExample: wxcli cc-agents update-logout --logout-reason LOGOUT_REASON\n\n\b\nExample --json-body: '{"logoutReason":"...","agentId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_LOGOUT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/agents/logout"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if logout_reason is not None:
            body["logoutReason"] = logout_reason
        if agent_id is not None:
            body["agentId"] = agent_id
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



_BODY_SKELETON_UPDATE_STATE_SESSION_1 = '{"channelType":["..."],"state":"...","auxCodeId":"...","reason":"...","agentId":"..."}'

@app.command("update-state-session-1", short_help="State Change.")
def update_state_session_1(
    state: str = typer.Option(None, "--state", help="It represents the current state of the user. Can be set to ```Available``` or ```Idle``` or ```LoggedOut``` or ```Reserved``` or ```Engaged``` or or ```EngagedOther``` ."),
    aux_code_id: str = typer.Option(None, "--aux-code-id", help="Auxiliary Codes are status codes which an agent can select in Webex Contact Center Agent Desktop. They are of two types: ```Idle``` and ```Wrap-Up``` codes, and every agent profile must have one of each for the agent to use. Idle codes are used to explain an agent's unavailability to take customer..."),
    reason: str = typer.Option(None, "--reason", help="It represents the reason of the last agent channel state change request, maximum length 128 characters."),
    agent_id: str = typer.Option(None, "--agent-id", help="User for which agent channel state change is initiated, maximum length 36 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """State Change.\n\n\b\nExample: wxcli cc-agents update-state-session-1 --json-body '{"channelType":["..."],"state":"..."}'\n\n\b\nExample --json-body: '{"channelType":["..."],"state":"...","auxCodeId":"...","reason":"...","agentId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_STATE_SESSION_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/agents/session/state"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if state is not None:
            body["state"] = state
        if aux_code_id is not None:
            body["auxCodeId"] = aux_code_id
        if reason is not None:
            body["reason"] = reason
        if agent_id is not None:
            body["agentId"] = agent_id
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



@app.command("create-reload-agents-1", short_help="Reload.")
def create_reload_agents_1(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reload."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/agents/reload"
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
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)


