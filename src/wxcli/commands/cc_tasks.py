import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-tasks.")


@app.command("list", short_help="Get Tasks.")
def cmd_list(
    channel_types: str = typer.Option(None, "--channel-types", help="Task channel type(s) permitted in response. Separate values with commas. Use lowercase. By default, there is no channelType filtering."),
    from_param: str = typer.Option(..., "--from", help="Filters tasks created after the given epoch timestamp (in milliseconds)."),
    to: str = typer.Option(None, "--to", help="Filters tasks created before the given epoch timestamp (in milliseconds); queries up to the present if timestamp is not specified."),
    page_size: str = typer.Option(None, "--page-size", help="Maximum page size in the response. Maximum allowed value is 1000. Defaults to 100 items per page."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Tasks.\n\n\b\nExample: wxcli cc-tasks list --from FROM_PARAM"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks"
    params = {}
    if channel_types is not None:
        params["channelTypes"] = channel_types
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if page_size is not None:
        params["pageSize"] = page_size
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id')], limit=limit)



_BODY_SKELETON_CREATE = '{"destination":"...","entryPointId":"...","mediaType":"...","attributes":{},"outboundType":"...","origin":"...","callback":{"callbackOrigin":"...","callbackType":"..."},"customAttributes":{}}'

@app.command("create", short_help="Create Task.")
def create(
    destination: str = typer.Option(None, "--destination", help="(required) A valid customer DN, on which the response is expected, maximum length 36 characters."),
    entry_point_id: str = typer.Option(None, "--entry-point-id", help="(required) An entryPointId for respective task. For ```CALLBACK``` and ```OUTDIAL``` this should be an outboundEP. For ```EXECUTE_FLOW``` this should be an inboundEP which is mapped to a flow that will be triggered, maximum length 36 characters."),
    outbound_type: str = typer.Option(None, "--outbound-type", help="The outbound type for the task. Supported values are ```CALLBACK```, ```OUTDIAL```, and ```EXECUTE_FLOW```. Use ```OUTDIAL``` when the user is logged into the Agent Desktop and needs to make an outbound call to the customer. Use ```CALLBACK``` when the user is not logged in and needs to schedule a..."),
    media_type: str = typer.Option(None, "--media-type", help="(required) The media type for the request. The ```telephony``` type is required for ```EXECUTE_FLOW``` and ```CALLBACK```. The supported value is ```telephony```."),
    origin: str = typer.Option(None, "--origin", help="The contact center number, which is an ANI Outdial number, that will be used while making a call to the customer. This field is mandatory for ```EXECUTE_FLOW``` and ```OUTDIAL``` type while it is optional for ```CALLBACK```. If not provided for ```CALLBACK``` type, default out-dial ANI..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Task.\n\n\b\nExample: wxcli cc-tasks create --destination DESTINATION --entry-point-id ENTRY_POINT_ID --media-type MEDIA_TYPE\n\n\b\nExample --json-body: '{"destination":"...","entryPointId":"...","mediaType":"...","attributes":{},"outboundType":"...","origin":"...","callback":{"callbackOrigin":"...","callbackType":"..."},"customAttributes":{}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if destination is not None:
            body["destination"] = destination
        if entry_point_id is not None:
            body["entryPointId"] = entry_point_id
        if outbound_type is not None:
            body["outboundType"] = outbound_type
        if media_type is not None:
            body["mediaType"] = media_type
        if origin is not None:
            body["origin"] = origin
        _missing = [f for f in ['destination', 'entryPointId', 'mediaType'] if f not in body or body[f] is None]
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



_BODY_SKELETON_UPDATE = '{"attributes":{}}'

@app.command("update", short_help="Update Task.")
def update(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Task.\n\n\b\nExample: wxcli cc-tasks update TASK_ID --json-body '{"attributes":{}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": task_id}, output=output, fields=fields)



@app.command("create-accept-tasks", short_help="Accept Task.")
def create_accept_tasks(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Accept Task.\n\n\b\nExample: wxcli cc-tasks create-accept-tasks TASK_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/accept"
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



@app.command("create-end-tasks", short_help="End Task.")
def create_end_tasks(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """End Task.\n\n\b\nExample: wxcli cc-tasks create-end-tasks TASK_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/end"
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



_BODY_SKELETON_CREATE_WRAPUP = '{"auxCodeId":"...","wrapUpReason":"..."}'

@app.command("create-wrapup", short_help="Wrap Up Task.")
def create_wrapup(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    aux_code_id: str = typer.Option(None, "--aux-code-id", help="(required) Auxiliary codes are status codes which an agent can select in Webex Contact Center Agent Desktop. They are of two types: ```Idle``` and ```Wrap-Up``` codes, and every agent profile must have one of each for the agent to use. Idle codes are used to explain an agent's unavailability to take customer..."),
    wrap_up_reason: str = typer.Option(None, "--wrap-up-reason", help="(required) Every wrap up reason will have an unique auxillary code. Use this field to specify the reason for wrapping up the call, maximum length 128 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Wrap Up Task.\n\n\b\nExample: wxcli cc-tasks create-wrapup TASK_ID --aux-code-id AUX_CODE_ID --wrap-up-reason WRAP_UP_REASON\n\n\b\nExample --json-body: '{"auxCodeId":"...","wrapUpReason":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_WRAPUP), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/wrapup"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if aux_code_id is not None:
            body["auxCodeId"] = aux_code_id
        if wrap_up_reason is not None:
            body["wrapUpReason"] = wrap_up_reason
        _missing = [f for f in ['auxCodeId', 'wrapUpReason'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_HOLD = '{"mediaResourceId":"..."}'

@app.command("create-hold", short_help="Hold Task.")
def create_hold(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    media_resource_id: str = typer.Option(None, "--media-resource-id", help="(required) It is an identifier of a media resource, maximum length 36 characters"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hold Task.\n\n\b\nExample: wxcli cc-tasks create-hold TASK_ID --media-resource-id MEDIA_RESOURCE_ID\n\n\b\nExample --json-body: '{"mediaResourceId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_HOLD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/hold"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if media_resource_id is not None:
            body["mediaResourceId"] = media_resource_id
        _missing = [f for f in ['mediaResourceId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_UNHOLD = '{"mediaResourceId":"..."}'

@app.command("create-unhold", short_help="Resume Task.")
def create_unhold(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    media_resource_id: str = typer.Option(None, "--media-resource-id", help="(required) It is an identifier of a media resource, maximum length 36 characters"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume Task.\n\n\b\nExample: wxcli cc-tasks create-unhold TASK_ID --media-resource-id MEDIA_RESOURCE_ID\n\n\b\nExample --json-body: '{"mediaResourceId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_UNHOLD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/unhold"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if media_resource_id is not None:
            body["mediaResourceId"] = media_resource_id
        _missing = [f for f in ['mediaResourceId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_REJECT = '{"mediaResourceId":"..."}'

@app.command("create-reject", short_help="Reject Task.")
def create_reject(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    media_resource_id: str = typer.Option(None, "--media-resource-id", help="(required) It is an identifier of a media resource, maximum length 36 characters"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reject Task.\n\n\b\nExample: wxcli cc-tasks create-reject TASK_ID --media-resource-id MEDIA_RESOURCE_ID\n\n\b\nExample --json-body: '{"mediaResourceId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/reject"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if media_resource_id is not None:
            body["mediaResourceId"] = media_resource_id
        _missing = [f for f in ['mediaResourceId'] if f not in body or body[f] is None]
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



@app.command("create-pause", short_help="Pause Recording Task.")
def create_pause(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause Recording Task.\n\n\b\nExample: wxcli cc-tasks create-pause TASK_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/record/pause"
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



_BODY_SKELETON_CREATE_RESUME = '{"autoResumed":true}'

@app.command("create-resume", short_help="Resume Recording Task.")
def create_resume(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    auto_resumed: bool = typer.Option(None, "--auto-resumed/--no-auto-resumed", help="(required) The setting to mention if the recording has to resume automatically."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume Recording Task.\n\n\b\nExample: wxcli cc-tasks create-resume TASK_ID --auto-resumed\n\n\b\nExample --json-body: '{"autoResumed":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_RESUME), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/record/resume"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if auto_resumed is not None:
            body["autoResumed"] = auto_resumed
        _missing = [f for f in ['autoResumed'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_TRANSFER_TASKS = '{"to":"...","destinationType":"..."}'

@app.command("create-transfer-tasks", short_help="Transfer Task.")
def create_transfer_tasks(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    to: str = typer.Option(None, "--to", help="(required) The user destination ID or the entry point ID to transfer, maximum length 43 characters."),
    destination_type: str = typer.Option(None, "--destination-type", help="(required) The user can transfer to another user in the team(```agent```), queue(```queue```), dial number(```dialNumber```), entry point(```entrypointDialNumber```)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Transfer Task.\n\n\b\nExample: wxcli cc-tasks create-transfer-tasks TASK_ID --to TO --destination-type DESTINATION_TYPE\n\n\b\nExample --json-body: '{"to":"...","destinationType":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TRANSFER_TASKS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/transfer"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if to is not None:
            body["to"] = to
        if destination_type is not None:
            body["destinationType"] = destination_type
        _missing = [f for f in ['to', 'destinationType'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_CONSULT = '{"to":"...","destinationType":"...","holdParticipants":true}'

@app.command("create-consult", short_help="Consult Task.")
def create_consult(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    to: str = typer.Option(None, "--to", help="(required) The destination ID to consult, maximum length 36 characters."),
    destination_type: str = typer.Option(None, "--destination-type", help="(required) The user can consult to another user in the team(```agent```), queue(```queue```), entry point(```entryPoint```) or dial number(```dialNumber```). When consulting an Entry Point (EP) that is associated with multiple Directory Numbers (DNs), the consult typically goes to one of the associated DNs."),
    hold_participants: bool = typer.Option(None, "--hold-participants/--no-hold-participants", help="This allows the caller to specify their preference for whether the main call should be placed on hold or not during consult."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Consult Task.\n\n\b\nExample: wxcli cc-tasks create-consult TASK_ID --to TO --destination-type DESTINATION_TYPE\n\n\b\nExample --json-body: '{"to":"...","destinationType":"...","holdParticipants":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CONSULT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/consult"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if to is not None:
            body["to"] = to
        if destination_type is not None:
            body["destinationType"] = destination_type
        if hold_participants is not None:
            body["holdParticipants"] = hold_participants
        _missing = [f for f in ['to', 'destinationType'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_CONFERENCE = '{"to":"...","agentId":"...","destinationType":"..."}'

@app.command("create-conference", short_help="Consult Conference Task.")
def create_conference(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    agent_id: str = typer.Option(None, "--agent-id", help="The unique Id of the user logged in as an agent."),
    to: str = typer.Option(None, "--to", help="(required) The destination ID to consult, maximum length 36 characters."),
    destination_type: str = typer.Option(None, "--destination-type", help="The user can consult to another user in the team(```agent```), dial number(```dialNumber```), entry point(```entryPoint```)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Consult Conference Task.\n\n\b\nExample: wxcli cc-tasks create-conference TASK_ID --to TO\n\n\b\nExample --json-body: '{"to":"...","agentId":"...","destinationType":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CONFERENCE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/consult/conference"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if agent_id is not None:
            body["agentId"] = agent_id
        if to is not None:
            body["to"] = to
        if destination_type is not None:
            body["destinationType"] = destination_type
        _missing = [f for f in ['to'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_TRANSFER_CONSULT = '{"to":"...","destinationType":"..."}'

@app.command("create-transfer-consult", short_help="Consult Transfer Task.")
def create_transfer_consult(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    to: str = typer.Option(None, "--to", help="(required) The consulted user destination ID to transfer, maximum length 36 characters."),
    destination_type: str = typer.Option(None, "--destination-type", help="(required) The user can transfer to another consulted user in the team(```agent```), dial number(```dialNumber```), entry point(```entryPoint```)"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Consult Transfer Task.\n\n\b\nExample: wxcli cc-tasks create-transfer-consult TASK_ID --to TO --destination-type DESTINATION_TYPE\n\n\b\nExample --json-body: '{"to":"...","destinationType":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TRANSFER_CONSULT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/consult/transfer"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if to is not None:
            body["to"] = to
        if destination_type is not None:
            body["destinationType"] = destination_type
        _missing = [f for f in ['to', 'destinationType'] if f not in body or body[f] is None]
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



@app.command("create-accept-consult", short_help="Consult Accept Task.")
def create_accept_consult(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Consult Accept Task.\n\n\b\nExample: wxcli cc-tasks create-accept-consult TASK_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/consult/accept"
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



@app.command("create-assign", short_help="Assign Task.")
def create_assign(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign Task.\n\n\b\nExample: wxcli cc-tasks create-assign TASK_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/assign"
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



_BODY_SKELETON_CREATE_END_CONSULT = '{"queueId":"..."}'

@app.command("create-end-consult", short_help="Consult End Task.")
def create_end_consult(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    queue_id: str = typer.Option(None, "--queue-id", help="The unique ID of a particular queue, maximum length 36 characters."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Consult End Task.\n\n\b\nExample: wxcli cc-tasks create-end-consult TASK_ID\n\n\b\nExample --json-body: '{"queueId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_END_CONSULT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/consult/end"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if queue_id is not None:
            body["queueId"] = queue_id
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



@app.command("create-exit", short_help="Exit Conference Task.")
def create_exit(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Exit Conference Task.\n\n\b\nExample: wxcli cc-tasks create-exit TASK_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/tasks/{task_id}/conference/exit"
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



@app.command("create-accept-preview-task", short_help="Accept Preview Task.")
def create_accept_preview_task(
    task_id: str = typer.Argument(help="UUID"),
    campaign_id: str = typer.Argument(help="UUID"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Accept Preview Task.\n\n\b\nExample: wxcli cc-tasks create-accept-preview-task TASK_ID CAMPAIGN_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/dialer/campaign/{campaign_id}/preview-task/{task_id}/accept"
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



@app.command("create-skip", short_help="Skip Preview Task.")
def create_skip(
    task_id: str = typer.Argument(help="UUID"),
    campaign_id: str = typer.Argument(help="UUID"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Skip Preview Task.\n\n\b\nExample: wxcli cc-tasks create-skip TASK_ID CAMPAIGN_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/dialer/campaign/{campaign_id}/preview-task/{task_id}/skip"
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



@app.command("create-remove", hidden=True)
@app.command("delete-preview-task", short_help="Remove Preview Task.")
def delete_preview_task(
    task_id: str = typer.Argument(help="UUID"),
    campaign_id: str = typer.Argument(help="UUID"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove Preview Task.\n\n\b\nExample: wxcli cc-tasks delete-preview-task TASK_ID CAMPAIGN_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/dialer/campaign/{campaign_id}/preview-task/{task_id}/remove"
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
        typer.echo("Removed.")
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_TASKS = '{"origin":{"id":"...","name":"..."},"destination":{"id":"...","type":"businessAddress"},"channelType":"telephony","channel":"...","channelParams":{"type":"telephony","entryPointId":"...","outboundType":"CALLBACK","callback":{"type":"immediate","origin":"web","number":"..."},"sipHeaders":{}},"flowSettings":{},"globalVariables":{}}'

@app.command("create-tasks", short_help="Create Task.")
def create_tasks(
    channel_type: str = typer.Option(None, "--channel-type", help="(required) Choices: telephony"),
    channel: str = typer.Option(None, "--channel", help="(required) Not applicable for telephony tasks. May be omitted or set to `null`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Task.\n\n\b\nExample: wxcli cc-tasks create-tasks --json-body '{"origin":{"id":"..."},"destination":{"id":"...","type":"businessAddress"},"channelType":"telephony","channel":"...","channelParams":{"type":"telephony","entryPointId":"...","outboundType":"CALLBACK"}}'\n\n\b\nExample --json-body: '{"origin":{"id":"...","name":"..."},"destination":{"id":"...","type":"businessAddress"},"channelType":"telephony","channel":"...","channelParams":{"type":"telephony","entryPointId":"...","outboundType":"CALLBACK","callback":{"type":"immediate","origin":"web","number":"..."},"sipHeaders":{}},"flowSettings":{},"globalVariables":{}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TASKS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/tasks"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if channel_type is not None:
            body["channelType"] = channel_type
        if channel is not None:
            body["channel"] = channel
        _missing = [f for f in ['channelType', 'channel'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_MESSAGES = '{"mediaType":"customMessaging","channelParams":{"type":"text","message":{"aliasId":"...","text":"...","timestamp":0,"attachments":[{"fileName":"...","mimeType":"...","fileUrl":"..."}]}}}'

@app.command("create-messages", short_help="Append Task Message.")
def create_messages(
    task_id: str = typer.Argument(help="UUID, from: wxcli cc-tasks list"),
    media_type: str = typer.Option(None, "--media-type", help="(required) Choices: customMessaging"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Append Task Message.\n\n\b\nExample: wxcli cc-tasks create-messages TASK_ID --json-body '{"mediaType":"customMessaging","channelParams":{"type":"text","message":{"aliasId":"...","text":"...","timestamp":0,"attachments":[{"fileName":"...","mimeType":"...","fileUrl":"..."}]}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_MESSAGES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/tasks/{task_id}/messages"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if media_type is not None:
            body["mediaType"] = media_type
        _missing = [f for f in ['mediaType'] if f not in body or body[f] is None]
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


