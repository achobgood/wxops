import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling calling-service.")


@app.command("list")
def cmd_list(
    tts_language: str = typer.Option(None, "--tts-language", help="Filter languages by TTS support."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Announcement Languages."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcementLanguages"
    params = {}
    if tts_language is not None:
        params["ttsLanguage"] = tts_language
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
    items = result.get("languages", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Name', 'name'), ('Code', 'code')], limit=limit)



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Voicemail Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/settings"
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



_BODY_SKELETON_UPDATE = '{"messageExpiryEnabled":true,"numberOfDaysForMessageExpiry":0,"strictDeletionEnabled":true,"voiceMessageForwardingEnabled":true}'

@app.command("update")
def update(
    message_expiry_enabled: bool = typer.Option(None, "--message-expiry-enabled/--no-message-expiry-enabled", help="Set to `true` to enable voicemail deletion and set the deletion conditions for expired messages."),
    number_of_days_for_message_expiry: str = typer.Option(None, "--number-of-days-for-message-expiry", help="Number of days after which messages expire."),
    strict_deletion_enabled: bool = typer.Option(None, "--strict-deletion-enabled/--no-strict-deletion-enabled", help="Set to `true` to delete all read and unread voicemail messages based on the time frame you set. Set to `false` to keep all the unread voicemail messages."),
    voice_message_forwarding_enabled: bool = typer.Option(None, "--voice-message-forwarding-enabled/--no-voice-message-forwarding-enabled", help="Set to `true` to allow people to configure the email forwarding of voicemails."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voicemail Settings\n\nExample --json-body:\n  '{"messageExpiryEnabled":true,"numberOfDaysForMessageExpiry":0,"strictDeletionEnabled":true,"voiceMessageForwardingEnabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if message_expiry_enabled is not None:
            body["messageExpiryEnabled"] = message_expiry_enabled
        if number_of_days_for_message_expiry is not None:
            body["numberOfDaysForMessageExpiry"] = number_of_days_for_message_expiry
        if strict_deletion_enabled is not None:
            body["strictDeletionEnabled"] = strict_deletion_enabled
        if voice_message_forwarding_enabled is not None:
            body["voiceMessageForwardingEnabled"] = voice_message_forwarding_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("show-rules")
def show_rules(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Voicemail Rules."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/rules"
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



_BODY_SKELETON_UPDATE_RULES = '{"defaultVoicemailPinEnabled":true,"defaultVoicemailPin":"...","expirePasscode":{"enabled":true,"numberOfDays":0},"changePasscode":{"enabled":true,"numberOfDays":0},"blockPreviousPasscodes":{"enabled":true,"numberOfPasscodes":0}}'

@app.command("update-rules")
def update_rules(
    default_voicemail_pin_enabled: bool = typer.Option(None, "--default-voicemail-pin-enabled/--no-default-voicemail-pin-enabled", help="Set to `true` to enable the default voicemail passcode."),
    default_voicemail_pin: str = typer.Option(None, "--default-voicemail-pin", help="Default voicemail passcode."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voicemail Rules\n\nExample --json-body:\n  '{"defaultVoicemailPinEnabled":true,"defaultVoicemailPin":"...","expirePasscode":{"enabled":true,"numberOfDays":0},"changePasscode":{"enabled":true,"numberOfDays":0},"blockPreviousPasscodes":{"enabled":true,"numberOfPasscodes":0}}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_RULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/rules"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if default_voicemail_pin_enabled is not None:
            body["defaultVoicemailPinEnabled"] = default_voicemail_pin_enabled
        if default_voicemail_pin is not None:
            body["defaultVoicemailPin"] = default_voicemail_pin
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("show-settings")
def show_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the organization Music on Hold configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/moh/settings"
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



_BODY_SKELETON_UPDATE_SETTINGS = '{"defaultOrgMoh":"..."}'

@app.command("update-settings")
def update_settings(
    default_org_moh: str = typer.Option(None, "--default-org-moh", help="Default org level Music on Hold option, can be one of two options: Choose between Opus Number 1 (Music On Hold used in other Cisco products like UCM) and existing legacy Music On Hold."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the organization Music on Hold configuration\n\nExample --json-body:\n  '{"defaultOrgMoh":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/moh/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if default_org_moh is not None:
            body["defaultOrgMoh"] = default_org_moh
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("show-large-org-status")
def show_large_org_status(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Large Organization Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/largeOrgStatus"
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



@app.command("show-call-captions")
def show_call_captions(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the organization call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callCaptions"
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



_BODY_SKELETON_UPDATE_CALL_CAPTIONS = '{"orgClosedCaptionsEnabled":true,"orgTranscriptsEnabled":true}'

@app.command("update-call-captions")
def update_call_captions(
    org_closed_captions_enabled: bool = typer.Option(None, "--org-closed-captions-enabled/--no-org-closed-captions-enabled", help="Enable or disable organization-level closed captions."),
    org_transcripts_enabled: bool = typer.Option(None, "--org-transcripts-enabled/--no-org-transcripts-enabled", help="Enable or disable organization-level transcripts."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the organization call captions settings\n\nExample --json-body:\n  '{"orgClosedCaptionsEnabled":true,"orgTranscriptsEnabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_CAPTIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callCaptions"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if org_closed_captions_enabled is not None:
            body["orgClosedCaptionsEnabled"] = org_closed_captions_enabled
        if org_transcripts_enabled is not None:
            body["orgTranscriptsEnabled"] = org_transcripts_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")


