import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling calling-service.")


@app.command("list")
def cmd_list(
    tts_language: str = typer.Option(None, "--tts-language", help="Filter languages by TTS support."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("languages", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Name', 'name'), ('Code', 'code')], limit=limit)



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    message_expiry_enabled: bool = typer.Option(None, "--message-expiry-enabled/--no-message-expiry-enabled", help="Set to `true` to enable voicemail deletion and set the delet"),
    number_of_days_for_message_expiry: str = typer.Option(None, "--number-of-days-for-message-expiry", help="Number of days after which messages expire."),
    strict_deletion_enabled: bool = typer.Option(None, "--strict-deletion-enabled/--no-strict-deletion-enabled", help="Set to `true` to delete all read and unread voicemail messag"),
    voice_message_forwarding_enabled: bool = typer.Option(None, "--voice-message-forwarding-enabled/--no-voice-message-forwarding-enabled", help="Set to `true` to allow people to configure the email forward"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voicemail Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("show-rules")
def show_rules(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-rules")
def update_rules(
    default_voicemail_pin_enabled: bool = typer.Option(None, "--default-voicemail-pin-enabled/--no-default-voicemail-pin-enabled", help="Set to `true` to enable the default voicemail passcode."),
    default_voicemail_pin: str = typer.Option(None, "--default-voicemail-pin", help="Default voicemail passcode."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voicemail Rules\n\nExample --json-body:\n  '{"defaultVoicemailPinEnabled":true,"defaultVoicemailPin":"...","expirePasscode":{"enabled":true,"numberOfDays":0},"changePasscode":{"enabled":true,"numberOfDays":0},"blockPreviousPasscodes":{"enabled":true,"numberOfPasscodes":0}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/rules"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("show-settings")
def show_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-settings")
def update_settings(
    default_org_moh: str = typer.Option(None, "--default-org-moh", help="Default org level Music on Hold option, can be one of two op"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the organization Music on Hold configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/moh/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if default_org_moh is not None:
            body["defaultOrgMoh"] = default_org_moh
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-large-org-status")
def show_large_org_status(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("show-call-captions")
def show_call_captions(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-call-captions")
def update_call_captions(
    org_closed_captions_enabled: bool = typer.Option(None, "--org-closed-captions-enabled/--no-org-closed-captions-enabled", help="Enable or disable organization-level closed captions."),
    org_transcripts_enabled: bool = typer.Option(None, "--org-transcripts-enabled/--no-org-transcripts-enabled", help="Enable or disable organization-level transcripts."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the organization call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callCaptions"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")


