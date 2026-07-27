import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling customer-assist.")


@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Wrap Up Reasons."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons"
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
    items = result.get("wrapupReasons", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description'), ('Number Of Queues Assigned', 'numberOfQueuesAssigned')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","description":"...","queues":["..."],"assignAllQueuesEnabled":true}'

@app.command("create")
def create(
    name: str = typer.Option(None, "--name", help="(required) Name of the wrap-up reason."),
    description: str = typer.Option(None, "--description", help="Description of the wrap-up reason."),
    assign_all_queues_enabled: bool = typer.Option(None, "--assign-all-queues-enabled/--no-assign-all-queues-enabled", help="Denotes whether all queues are assigned to the wrap-up reason."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Wrap Up Reason\n\nExample --json-body:\n  '{"name":"...","description":"...","queues":["..."],"assignAllQueuesEnabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if assign_all_queues_enabled is not None:
            body["assignAllQueuesEnabled"] = assign_all_queues_enabled
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
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



@app.command("show")
def show(
    wrapup_reason_id: str = typer.Argument(help="wrapupReasonId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Wrap Up Reason."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/{wrapup_reason_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","description":"...","queuesToAssign":["..."],"queuesToUnassign":["..."],"assignAllQueuesEnabled":true,"unassignAllQueuesEnabled":true}'

@app.command("update")
def update(
    wrapup_reason_id: str = typer.Argument(help="wrapupReasonId"),
    name: str = typer.Option(None, "--name", help="Name of the wrap-up reason."),
    description: str = typer.Option(None, "--description", help="Description of the wrap-up reason."),
    assign_all_queues_enabled: bool = typer.Option(None, "--assign-all-queues-enabled/--no-assign-all-queues-enabled", help="Denotes whether all queues are assigned to the wrap-up reason."),
    unassign_all_queues_enabled: bool = typer.Option(None, "--unassign-all-queues-enabled/--no-unassign-all-queues-enabled", help="Denotes whether all queues are unassigned from the wrap-up reason."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Wrap Up Reason\n\nExample --json-body:\n  '{"name":"...","description":"...","queuesToAssign":["..."],"queuesToUnassign":["..."],"assignAllQueuesEnabled":true,"unassignAllQueuesEnabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/{wrapup_reason_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if assign_all_queues_enabled is not None:
            body["assignAllQueuesEnabled"] = assign_all_queues_enabled
        if unassign_all_queues_enabled is not None:
            body["unassignAllQueuesEnabled"] = unassign_all_queues_enabled
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
        emit({"status": "updated", "id": wrapup_reason_id}, output=output, fields=fields)



@app.command("delete")
def delete(
    wrapup_reason_id: str = typer.Argument(help="wrapupReasonId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Wrap Up Reason."""
    if not force:
        typer.confirm(f"Delete {wrapup_reason_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/{wrapup_reason_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {wrapup_reason_id}")
    else:
        emit({"status": "deleted", "id": wrapup_reason_id}, output=output, fields=fields)



_BODY_SKELETON_VALIDATE_WRAP_UP = '{"name":"..."}'

@app.command("validate-wrap-up")
def validate_wrap_up(
    name: str = typer.Option(None, "--name", help="Name of the wrap-up reason."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate Wrap Up Reason\n\nExample --json-body:\n  '{"name":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_WRAP_UP), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/actions/validateName/invoke"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-available-queues")
def list_available_queues(
    wrapup_reason_id: str = typer.Argument(help="wrapupReasonId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Available Queues."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/{wrapup_reason_id}/availableQueues"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Location Name', 'locationName'), ('Location ID', 'locationId'), ('Phone Number', 'phoneNumber')], limit=limit)



@app.command("list-settings")
def list_settings(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Wrap Up Reason Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/locations/{location_id}/queues/{queue_id}/wrapup/settings"
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
    items = result.get("wrapupReasons", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description'), ('Is Default Enabled', 'isDefaultEnabled')], limit=limit)



_BODY_SKELETON_UPDATE_SETTINGS = '{"wrapupReasons":["..."],"defaultWrapupReasonId":"...","wrapupTimerEnabled":true,"wrapupTimer":0}'

@app.command("update-settings")
def update_settings(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    default_wrapup_reason_id: str = typer.Option(None, "--default-wrapup-reason-id", help="Unique wrap-up identifier."),
    wrapup_timer_enabled: bool = typer.Option(None, "--wrapup-timer-enabled/--no-wrapup-timer-enabled", help="Denotes whether the wrap-up timer is enabled."),
    wrapup_timer: str = typer.Option(None, "--wrapup-timer", help="Wrap up timer value in seconds."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Wrap Up Reason Settings\n\nExample --json-body:\n  '{"wrapupReasons":["..."],"defaultWrapupReasonId":"...","wrapupTimerEnabled":true,"wrapupTimer":0}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/locations/{location_id}/queues/{queue_id}/wrapup/settings"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if default_wrapup_reason_id is not None:
            body["defaultWrapupReasonId"] = default_wrapup_reason_id
        if wrapup_timer_enabled is not None:
            body["wrapupTimerEnabled"] = wrapup_timer_enabled
        if wrapup_timer is not None:
            body["wrapupTimer"] = wrapup_timer
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



@app.command("show-screen-pop")
def show_screen_pop(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Screen Pop Configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/cxEssentials/screenPop"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SCREEN_POP = '{"enabled":true,"screenPopUrl":"...","desktopLabel":"...","queryParams":{"example_param_1":"...","example_param_2":"...","example_param_3":"..."}}'

@app.command("update-screen-pop")
def update_screen_pop(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable/disable screen pop."),
    screen_pop_url: str = typer.Option(None, "--screen-pop-url", help="The screen pop URL that integrates Webex calls with other business apps like CRM, ticketing tools, and order entry systems."),
    desktop_label: str = typer.Option(None, "--desktop-label", help="A label for the screen pop configuration."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Screen Pop Configuration\n\nExample --json-body:\n  '{"enabled":true,"screenPopUrl":"...","desktopLabel":"...","queryParams":{"example_param_1":"...","example_param_2":"...","example_param_3":"..."}}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SCREEN_POP), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/cxEssentials/screenPop"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if screen_pop_url is not None:
            body["screenPopUrl"] = screen_pop_url
        if desktop_label is not None:
            body["desktopLabel"] = desktop_label
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



@app.command("list-available-agents")
def list_available_agents(
    location_id: str = typer.Argument(help="locationId"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of available agents with Customer Assist license when `true`, otherwise returns the list of available agents with Customer Experience Basic license."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Agents."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/cxEssentials/agents/availableAgents"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
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
    items = result.get("agents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Last Name', 'lastName'), ('First Name', 'firstName'), ('Type', 'type')], limit=limit)



@app.command("show-call-recordings")
def show_call_recordings(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Queue Call Recording Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/cxEssentials/callRecordings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_RECORDINGS = '{"enabled":true,"record":"...","notification":{"type":"...","enabled":true},"repeat":{"interval":0,"enabled":true},"startStopAnnouncement":{"internalCallsEnabled":true,"pstnCallsEnabled":true}}'

@app.command("update-call-recordings")
def update_call_recordings(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether call recording is enabled for the queue."),
    record: str = typer.Option(None, "--record", help="When to record. Live-verified value: `Always`. Other values are not asserted here because they have not been verified against the live API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Queue Call Recording Settings\n\nExample --json-body:\n  '{"enabled":true,"record":"...","notification":{"type":"...","enabled":true},"repeat":{"interval":0,"enabled":true},"startStopAnnouncement":{"internalCallsEnabled":true,"pstnCallsEnabled":true}}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_RECORDINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/cxEssentials/callRecordings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if record is not None:
            body["record"] = record
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)


