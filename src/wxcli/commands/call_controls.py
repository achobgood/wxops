import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling call-controls.")


_BODY_SKELETON_CREATE = '{"destination":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'

@app.command("create")
def create(
    destination: str = typer.Option(None, "--destination", help="(required) The destination to be dialed. The destination can be digits or a URI. Some examples for destination include: `1234`, `2223334444`, `+12223334444`, `*73`, `tel:+12223334444`, `user@company.domain`, and `sip:user@company.domain`."),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to use for the call. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint). Mutually exclusive with `singleNumberReachPhoneNumber`."),
    single_number_reach_phone_number: str = typer.Option(None, "--single-number-reach-phone-number", help="The Single Number Reach phone number to use for the call. Mutually exclusive with `endpointId`."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Dial\n\nExample --json-body:\n  '{"destination":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/dial"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if destination is not None:
            body["destination"] = destination
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if single_number_reach_phone_number is not None:
            body["singleNumberReachPhoneNumber"] = single_number_reach_phone_number
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['destination'] if f not in body or body[f] is None]
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
        if isinstance(result, dict) and "callId" in result:
            typer.echo(f"Created: {result['callId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_ANSWER_CALLS = '{"callId":"...","endpointId":"...","lineOwnerId":"..."}'

@app.command("create-answer-calls")
def create_answer_calls(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to be answered."),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to answer the call on. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint)."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Answer\n\nExample --json-body:\n  '{"callId":"...","endpointId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ANSWER_CALLS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/answer"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_REJECT = '{"callId":"...","action":{},"lineOwnerId":"..."}'

@app.command("create-reject")
def create_reject(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to be rejected."),
    action: str = typer.Option(None, "--action", help="The rejection action to apply to the call. The busy action is applied if no specific action is provided."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reject\n\nExample --json-body:\n  '{"callId":"...","action":{},"lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_REJECT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/reject"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if action is not None:
            body["action"] = action
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_HANGUP_CALLS = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-hangup-calls")
def create_hangup_calls(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to hangup."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hangup\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_HANGUP_CALLS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/hangup"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_HOLD = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-hold")
def create_hold(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to hold."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hold\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_HOLD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/hold"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_RESUME = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-resume")
def create_resume(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to resume."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_RESUME), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/resume"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_MUTE = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-mute")
def create_mute(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to mute."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mute\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_MUTE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/mute"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_UNMUTE = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-unmute")
def create_unmute(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to unmute."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unmute\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_UNMUTE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/unmute"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_DIVERT = '{"callId":"...","destination":"...","toVoicemail":true,"lineOwnerId":"..."}'

@app.command("create-divert")
def create_divert(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to divert."),
    destination: str = typer.Option(None, "--destination", help="The destination to divert the call to. If toVoicemail is false, destination is required. The destination can be digits or a URI. Some examples for destination include: `1234`, `2223334444`, `+12223334444`, `*73`, `tel:+12223334444`, `user@company.domain`, `sip:user@company.domain`"),
    to_voicemail: bool = typer.Option(None, "--to-voicemail/--no-to-voicemail", help="If set to true, the call is diverted to voicemail. If no destination is specified, the call is diverted to the user's own voicemail. If a destination is specified, the call is diverted to the specified user's voicemail."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Divert\n\nExample --json-body:\n  '{"callId":"...","destination":"...","toVoicemail":true,"lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DIVERT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/divert"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if destination is not None:
            body["destination"] = destination
        if to_voicemail is not None:
            body["toVoicemail"] = to_voicemail
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_TRANSFER = '{"callId1":"...","callId2":"...","destination":"...","lineOwnerId":"..."}'

@app.command("create-transfer")
def create_transfer(
    call_id1: str = typer.Option(None, "--call-id1", help="The call identifier of the first call to transfer. This parameter is mandatory if either `callId2` or `destination` is provided."),
    call_id2: str = typer.Option(None, "--call-id2", help="The call identifier of the second call to transfer. This parameter is mandatory if `callId1` is provided and `destination` is not provided."),
    destination: str = typer.Option(None, "--destination", help="The destination to be transferred to. The destination can be digits or a URI. Some examples for destination include: `1234`, `2223334444`, `+12223334444`, `tel:+12223334444`, `user@company.domain`, `sip:user@company.domain`. This parameter is mandatory if `callId1` is provided and `callId2` is not..."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Transfer\n\nExample --json-body:\n  '{"callId1":"...","callId2":"...","destination":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TRANSFER), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/transfer"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id1 is not None:
            body["callId1"] = call_id1
        if call_id2 is not None:
            body["callId2"] = call_id2
        if destination is not None:
            body["destination"] = destination
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "callId" in result:
            typer.echo(f"Created: {result['callId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_PARK = '{"callId":"...","destination":"...","isGroupPark":true,"lineOwnerId":"..."}'

@app.command("create-park")
def create_park(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to park."),
    destination: str = typer.Option(None, "--destination", help="Identifes where the call is to be parked. If not provided, the call is parked against the parking user. The destination can be digits or a URI. Some examples for destination include: `1234`, `2223334444`, `+12223334444`, `*73`, `tel:+12223334444`, `user@company.domain`, `sip:user@company.domain`"),
    is_group_park: bool = typer.Option(None, "--is-group-park/--no-is-group-park", help="If set to`true`, the call is parked against an automatically selected member of the user's call park group and the destination parameter is ignored."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Park\n\nExample --json-body:\n  '{"callId":"...","destination":"...","isGroupPark":true,"lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_PARK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/park"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if destination is not None:
            body["destination"] = destination
        if is_group_park is not None:
            body["isGroupPark"] = is_group_park
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_RETRIEVE = '{"destination":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'

@app.command("create-retrieve")
def create_retrieve(
    destination: str = typer.Option(None, "--destination", help="Identifies where the call is parked. The number field from the park command response can be used as the destination for the retrieve command. If not provided, the call parked against the retrieving user is retrieved. The destination can be digits or a URI. Some examples for destination include:..."),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to use for the retrieval. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint). Mutually exclusive with `singleNumberReachPhoneNumber`."),
    single_number_reach_phone_number: str = typer.Option(None, "--single-number-reach-phone-number", help="The Single Number Reach phone number to use for the retrieval. Mutually exclusive with `endpointId`."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve\n\nExample --json-body:\n  '{"destination":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_RETRIEVE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/retrieve"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if destination is not None:
            body["destination"] = destination
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if single_number_reach_phone_number is not None:
            body["singleNumberReachPhoneNumber"] = single_number_reach_phone_number
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "callId" in result:
            typer.echo(f"Created: {result['callId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_START_RECORDING = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-start-recording")
def create_start_recording(
    call_id: str = typer.Option(None, "--call-id", help="The call identifier of the call to start recording."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Start Recording\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_START_RECORDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/startRecording"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



_BODY_SKELETON_CREATE_STOP_RECORDING = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-stop-recording")
def create_stop_recording(
    call_id: str = typer.Option(None, "--call-id", help="The call identifier of the call to stop recording."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stop Recording\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_STOP_RECORDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/stopRecording"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



_BODY_SKELETON_CREATE_PAUSE_RECORDING = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-pause-recording")
def create_pause_recording(
    call_id: str = typer.Option(None, "--call-id", help="The call identifier of the call to pause recording."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause Recording\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_PAUSE_RECORDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/pauseRecording"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



_BODY_SKELETON_CREATE_RESUME_RECORDING = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-resume-recording")
def create_resume_recording(
    call_id: str = typer.Option(None, "--call-id", help="The call identifier of the call to resume recording."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume Recording\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_RESUME_RECORDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/resumeRecording"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



_BODY_SKELETON_CREATE_TRANSMIT_DTMF = '{"callId":"...","dtmf":"...","lineOwnerId":"..."}'

@app.command("create-transmit-dtmf")
def create_transmit_dtmf(
    call_id: str = typer.Option(None, "--call-id", help="The call identifier of the call to transmit DTMF digits for."),
    dtmf: str = typer.Option(None, "--dtmf", help="The DTMF digits to transmit. Each digit must be part of the following set: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, *, #, A, B, C, D]`. A comma \",\" may be included to indicate a pause between digits. For the value '1,234' the DTMF 1 digit is initially sent. After a pause, the DTMF 2, 3, and 4 digits are..."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Transmit DTMF\n\nExample --json-body:\n  '{"callId":"...","dtmf":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TRANSMIT_DTMF), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/transmitDtmf"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if dtmf is not None:
            body["dtmf"] = dtmf
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



_BODY_SKELETON_CREATE_PUSH = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-push")
def create_push(
    call_id: str = typer.Option(None, "--call-id", help="The call identifier of the call to push."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Push\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_PUSH), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/push"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



_BODY_SKELETON_CREATE_PICKUP = '{"target":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'

@app.command("create-pickup")
def create_pickup(
    target: str = typer.Option(None, "--target", help="Identifies the user to pickup an incoming call from. If not provided, an incoming call to the user's call pickup group is picked up. The target can be digits or a URI. Some examples for target include: `1234`, `2223334444`, `+12223334444`, `tel:+12223334444`, `user@company.domain`,..."),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to use for the pickup. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint). Mutually exclusive with `singleNumberReachPhoneNumber`."),
    single_number_reach_phone_number: str = typer.Option(None, "--single-number-reach-phone-number", help="The Single Number Reach phone number to use for the pickup. Mutually exclusive with `endpointId`."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pickup\n\nExample --json-body:\n  '{"target":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_PICKUP), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/pickup"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if target is not None:
            body["target"] = target
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if single_number_reach_phone_number is not None:
            body["singleNumberReachPhoneNumber"] = single_number_reach_phone_number
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "callId" in result:
            typer.echo(f"Created: {result['callId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_BARGE_IN = '{"target":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'

@app.command("create-barge-in")
def create_barge_in(
    target: str = typer.Option(None, "--target", help="(required) Identifies the user to barge-in on. The target can be digits or a URI. Some examples for target include: `1234`, `2223334444`, `+12223334444`, `tel:+12223334444`, `user@company.domain`, `sip:user@company.domain`"),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to use for the barge-in. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint). Mutually exclusive with `singleNumberReachPhoneNumber`."),
    single_number_reach_phone_number: str = typer.Option(None, "--single-number-reach-phone-number", help="The Single Number Reach phone number to use for the barge-in. Mutually exclusive with `endpointId`."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Barge In\n\nExample --json-body:\n  '{"target":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BARGE_IN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/bargeIn"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if target is not None:
            body["target"] = target
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if single_number_reach_phone_number is not None:
            body["singleNumberReachPhoneNumber"] = single_number_reach_phone_number
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['target'] if f not in body or body[f] is None]
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
        if isinstance(result, dict) and "callId" in result:
            typer.echo(f"Created: {result['callId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("list")
def cmd_list(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Calls."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Call ID', 'id'), ('Personality', 'personality'), ('State', 'state'), ('Remote Party', 'remoteParty.name')], limit=limit)



@app.command("show")
def show(
    call_id: str = typer.Argument(help="callId"),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/{call_id}"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-history")
def list_history(
    type_param: str = typer.Option(None, "--type", help="Choices: placed, missed, received"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Call History."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/history"
    params = {}
    if type_param is not None:
        params["type"] = type_param
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Type', 'type'), ('Name', 'name'), ('Number', 'number'), ('Time', 'time')], limit=limit)



_BODY_SKELETON_CREATE_PULL = '{"endpointId":"...","lineOwnerId":"..."}'

@app.command("create-pull")
def create_pull(
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to use for the retrieval. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint)."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pull\n\nExample --json-body:\n  '{"endpointId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_PULL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/pull"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "callId" in result:
            typer.echo(f"Created: {result['callId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_DIAL_MEMBERS = '{"destination":"...","endpointId":"...","singleNumberReachPhoneNumber":"..."}'

@app.command("create-dial-members")
def create_dial_members(
    member_id: str = typer.Argument(help="memberId"),
    destination: str = typer.Option(None, "--destination", help="(required) The destination to be dialed. The destination can be digits or a URI. Some examples for destination include: `1234`, `2223334444`, `+12223334444`, `*73`, `tel:+12223334444`, `user@company.domain`, and `sip:user@company.domain`."),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to use for the call. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint). Mutually exclusive with `singleNumberReachPhoneNumber`."),
    single_number_reach_phone_number: str = typer.Option(None, "--single-number-reach-phone-number", help="The Single Number Reach phone number to use for the call. Mutually exclusive with `endpointId`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Dial by Member ID\n\nExample --json-body:\n  '{"destination":"...","endpointId":"...","singleNumberReachPhoneNumber":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DIAL_MEMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/dial"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if destination is not None:
            body["destination"] = destination
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if single_number_reach_phone_number is not None:
            body["singleNumberReachPhoneNumber"] = single_number_reach_phone_number
        _missing = [f for f in ['destination'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "callId" in result:
            typer.echo(f"Created: {result['callId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_ANSWER_MEMBERS = '{"callId":"...","endpointId":"..."}'

@app.command("create-answer-members")
def create_answer_members(
    member_id: str = typer.Argument(help="memberId"),
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to be answered."),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to answer the call on. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Answer by Member ID\n\nExample --json-body:\n  '{"callId":"...","endpointId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ANSWER_MEMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/answer"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



_BODY_SKELETON_CREATE_HANGUP_MEMBERS = '{"callId":"..."}'

@app.command("create-hangup-members")
def create_hangup_members(
    member_id: str = typer.Argument(help="memberId"),
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to hangup."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hangup by Member ID\n\nExample --json-body:\n  '{"callId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_HANGUP_MEMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/hangup"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



@app.command("list-calls-members")
def list_calls_members(
    member_id: str = typer.Argument(help="memberId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Calls by Member ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/calls"
    params = {}
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-calls-members")
def show_calls_members(
    member_id: str = typer.Argument(help="memberId"),
    call_id: str = typer.Argument(help="callId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Details by Member ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/calls/{call_id}"
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



_BODY_SKELETON_CREATE_DIAL_ME = '{"destination":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'

@app.command("create-dial-me")
def create_dial_me(
    destination: str = typer.Option(None, "--destination", help="(required) The destination to be dialed. The destination can be digits or a URI. Some examples for destination include: `1234`, `2223334444`, `+12223334444`, `*73`, `tel:+12223334444`, `user@company.domain`, and `sip:user@company.domain`."),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to use for the call. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint). Mutually exclusive with `singleNumberReachPhoneNumber`."),
    single_number_reach_phone_number: str = typer.Option(None, "--single-number-reach-phone-number", help="The Single Number Reach phone number to use for the call. Mutually exclusive with `endpointId`."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Dial\n\nExample --json-body:\n  '{"destination":"...","endpointId":"...","singleNumberReachPhoneNumber":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DIAL_ME), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/me/dial"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if destination is not None:
            body["destination"] = destination
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if single_number_reach_phone_number is not None:
            body["singleNumberReachPhoneNumber"] = single_number_reach_phone_number
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['destination'] if f not in body or body[f] is None]
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
        if isinstance(result, dict) and "callId" in result:
            typer.echo(f"Created: {result['callId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_ANSWER_ME = '{"callId":"...","endpointId":"...","lineOwnerId":"..."}'

@app.command("create-answer-me")
def create_answer_me(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to be answered."),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help="The ID of the device or application to answer the call on. The `endpointId` must be one of the endpointIds returned by the [Get Preferred Answer Endpoint API](/docs/api/v1/user-call-settings-2-2/get-preferred-answer-endpoint)."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Answer\n\nExample --json-body:\n  '{"callId":"...","endpointId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ANSWER_ME), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/me/answer"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_HANGUP_ME = '{"callId":"...","lineOwnerId":"..."}'

@app.command("create-hangup-me")
def create_hangup_me(
    call_id: str = typer.Option(None, "--call-id", help="(required) The call identifier of the call to hangup."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hangup\n\nExample --json-body:\n  '{"callId":"...","lineOwnerId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_HANGUP_ME), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/me/hangup"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
        _missing = [f for f in ['callId'] if f not in body or body[f] is None]
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



@app.command("list-calls-me")
def list_calls_me(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Calls."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/me/calls"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-calls-me")
def show_calls_me(
    call_id: str = typer.Argument(help="callId"),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there is a secondary line on a device owned by the user invoking the API."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/me/calls/{call_id}"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


