import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling calling-service-settings.")


@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Announcement Languages."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcementLanguages"
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
    items = result.get("announcementLanguages", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Voicemail Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/settings"
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
    message_expiry_enabled: bool = typer.Option(None, "--message-expiry-enabled/--no-message-expiry-enabled", help=""),
    number_of_days_for_message_expiry: str = typer.Option(None, "--number-of-days-for-message-expiry", help=""),
    strict_deletion_enabled: bool = typer.Option(None, "--strict-deletion-enabled/--no-strict-deletion-enabled", help=""),
    voice_message_forwarding_enabled: bool = typer.Option(None, "--voice-message-forwarding-enabled/--no-voice-message-forwarding-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voicemail Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/settings"
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-rules")
def list_rules(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Voicemail Rules."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/rules"
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
    items = result.get("rules", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-rules")
def update_rules(
    default_voicemail_pin_enabled: bool = typer.Option(None, "--default-voicemail-pin-enabled/--no-default-voicemail-pin-enabled", help=""),
    default_voicemail_pin: str = typer.Option(None, "--default-voicemail-pin", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voicemail Rules."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemail/rules"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if default_voicemail_pin_enabled is not None:
            body["defaultVoicemailPinEnabled"] = default_voicemail_pin_enabled
        if default_voicemail_pin is not None:
            body["defaultVoicemailPin"] = default_voicemail_pin
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



@app.command("show-settings")
def show_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the organization Music on Hold configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/moh/settings"
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



@app.command("update-settings")
def update_settings(
    default_org_moh: str = typer.Option(None, "--default-org-moh", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the organization Music on Hold configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/moh/settings"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if default_org_moh is not None:
            body["defaultOrgMoh"] = default_org_moh
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



@app.command("show-call-captions")
def show_call_captions(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the organization call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callCaptions"
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



@app.command("update-call-captions")
def update_call_captions(
    org_closed_captions_enabled: bool = typer.Option(None, "--org-closed-captions-enabled/--no-org-closed-captions-enabled", help=""),
    org_transcripts_enabled: bool = typer.Option(None, "--org-transcripts-enabled/--no-org-transcripts-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the organization call captions settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callCaptions"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if org_closed_captions_enabled is not None:
            body["orgClosedCaptionsEnabled"] = org_closed_captions_enabled
        if org_transcripts_enabled is not None:
            body["orgTranscriptsEnabled"] = org_transcripts_enabled
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



@app.command("list-large-org-status")
def list_large_org_status(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Large Organization Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/largeOrgStatus"
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
    items = result.get("largeOrgStatus", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


