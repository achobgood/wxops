import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling call-controls.")


@app.command("create")
def create(
    destination: str = typer.Option(None, "--destination", help=""),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Dial."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/dial"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if destination is not None:
            body["destination"] = destination
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
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



@app.command("create-answer-calls")
def create_answer_calls(
    call_id: str = typer.Option(None, "--call-id", help=""),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Answer."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/answer"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
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



@app.command("create-reject")
def create_reject(
    call_id: str = typer.Option(None, "--call-id", help=""),
    action: str = typer.Option(None, "--action", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reject."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/reject"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if action is not None:
            body["action"] = action
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



@app.command("create-hangup-calls")
def create_hangup_calls(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hangup."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/hangup"
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



@app.command("create-hold")
def create_hold(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hold."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/hold"
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



@app.command("create-resume")
def create_resume(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/resume"
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
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mute."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/mute"
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



@app.command("create-unmute")
def create_unmute(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unmute."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/unmute"
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



@app.command("create-divert")
def create_divert(
    call_id: str = typer.Option(None, "--call-id", help=""),
    destination: str = typer.Option(None, "--destination", help=""),
    to_voicemail: bool = typer.Option(None, "--to-voicemail/--no-to-voicemail", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Divert."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/divert"
    if json_body:
        body = json.loads(json_body)
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



@app.command("create-transfer")
def create_transfer(
    call_id1: str = typer.Option(None, "--call-id1", help=""),
    call_id2: str = typer.Option(None, "--call-id2", help=""),
    destination: str = typer.Option(None, "--destination", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Transfer."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/transfer"
    if json_body:
        body = json.loads(json_body)
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



@app.command("create-park")
def create_park(
    call_id: str = typer.Option(None, "--call-id", help=""),
    destination: str = typer.Option(None, "--destination", help=""),
    is_group_park: bool = typer.Option(None, "--is-group-park/--no-is-group-park", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Park."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/park"
    if json_body:
        body = json.loads(json_body)
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



@app.command("create-retrieve")
def create_retrieve(
    destination: str = typer.Option(None, "--destination", help=""),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/retrieve"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if destination is not None:
            body["destination"] = destination
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
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



@app.command("create-start-recording")
def create_start_recording(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Start Recording."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/startRecording"
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



@app.command("create-stop-recording")
def create_stop_recording(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stop Recording."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/stopRecording"
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



@app.command("create-pause-recording")
def create_pause_recording(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause Recording."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/pauseRecording"
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



@app.command("create-resume-recording")
def create_resume_recording(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume Recording."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/resumeRecording"
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



@app.command("create-transmit-dtmf")
def create_transmit_dtmf(
    call_id: str = typer.Option(None, "--call-id", help=""),
    dtmf: str = typer.Option(None, "--dtmf", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Transmit DTMF."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/transmitDtmf"
    if json_body:
        body = json.loads(json_body)
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



@app.command("create-push")
def create_push(
    call_id: str = typer.Option(None, "--call-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Push."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/push"
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



@app.command("create-pickup")
def create_pickup(
    target: str = typer.Option(None, "--target", help=""),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pickup."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/pickup"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if target is not None:
            body["target"] = target
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
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



@app.command("create-barge-in")
def create_barge_in(
    target: str = typer.Option(None, "--target", help=""),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Barge In."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/bargeIn"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if target is not None:
            body["target"] = target
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
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



@app.command("list")
def cmd_list(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, or virtual line for which there"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("calls", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Call ID', 'callId'), ('Personality', 'personality'), ('State', 'state'), ('Remote Party', 'remoteParty.name')], limit=limit)



@app.command("show")
def show(
    call_id: str = typer.Argument(help="callId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/{call_id}"
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



@app.command("list-history")
def list_history(
    type_param: str = typer.Option(None, "--type", help="The type of call history records to retrieve. If not specifi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("history", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Direction', 'direction'), ('Call Type', 'callType'), ('Start', 'startTime')], limit=limit)



@app.command("create-dial")
def create_dial(
    member_id: str = typer.Argument(help="memberId"),
    destination: str = typer.Option(None, "--destination", help=""),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Dial by Member ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/dial"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if destination is not None:
            body["destination"] = destination
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
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



@app.command("create-answer-members")
def create_answer_members(
    member_id: str = typer.Argument(help="memberId"),
    call_id: str = typer.Option(None, "--call-id", help=""),
    endpoint_id: str = typer.Option(None, "--endpoint-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Answer by Member ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/answer"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if call_id is not None:
            body["callId"] = call_id
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
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



@app.command("create-hangup-members")
def create_hangup_members(
    member_id: str = typer.Argument(help="memberId"),
    call_id: str = typer.Option(None, "--call-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Hangup by Member ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/hangup"
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



@app.command("list-calls")
def list_calls(
    member_id: str = typer.Argument(help="memberId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("calls", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Call ID', 'callId'), ('Personality', 'personality'), ('State', 'state')], limit=limit)



@app.command("show-calls")
def show_calls(
    member_id: str = typer.Argument(help="memberId"),
    call_id: str = typer.Argument(help="callId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Details by Member ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/members/{member_id}/calls/{call_id}"
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



@app.command("create-pull")
def create_pull(
    endpoint_id: str = typer.Option(None, "--endpoint-id", help=""),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pull."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/calls/pull"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if endpoint_id is not None:
            body["endpointId"] = endpoint_id
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


