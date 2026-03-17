import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling location-call-settings-voicemail.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Voicemail."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemail"
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
    items = result.get("voicemail", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    voicemail_transcription_enabled: bool = typer.Option(None, "--voicemail-transcription-enabled/--no-voicemail-transcription-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Location Voicemail."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemail"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if voicemail_transcription_enabled is not None:
            body["voicemailTranscriptionEnabled"] = voicemail_transcription_enabled
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



@app.command("list-voice-portal")
def list_voice_portal(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get VoicePortal."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicePortal"
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
    items = result.get("voicePortal", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-voice-portal")
def update_voice_portal(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help=""),
    language_code: str = typer.Option(None, "--language-code", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update VoicePortal."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicePortal"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if language_code is not None:
            body["languageCode"] = language_code
        if extension is not None:
            body["extension"] = extension
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
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



@app.command("list-passcode-rules")
def list_passcode_rules(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get VoicePortal Passcode Rule."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicePortal/passcodeRules"
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
    items = result.get("passcodeRules", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-voicemail-groups")
def list_voicemail_groups(
    location_id: str = typer.Option(None, "--location-id", help="Location to which the voicemail group belongs."),
    name: str = typer.Option(None, "--name", help="Search (Contains) based on voicemail group name"),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number or extension"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of events in the response. The maxi"),
    start: str = typer.Option(None, "--start", help="Offset from the first result that you want to fetch."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List VoicemailGroup."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/voicemailGroups"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
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
    items = result.get("voicemailGroups", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    voicemail_group_id: str = typer.Argument(help="voicemailGroupId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Voicemail Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/{voicemail_group_id}"
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



@app.command("update-voicemail-groups")
def update_voicemail_groups(
    location_id: str = typer.Argument(help="locationId"),
    voicemail_group_id: str = typer.Argument(help="voicemailGroupId"),
    name: str = typer.Option(None, "--name", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    passcode: str = typer.Option(None, "--passcode", help=""),
    language_code: str = typer.Option(None, "--language-code", help=""),
    greeting: str = typer.Option(None, "--greeting", help="e.g. CUSTOM"),
    greeting_description: str = typer.Option(None, "--greeting-description", help=""),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Location Voicemail Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/{voicemail_group_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if enabled is not None:
            body["enabled"] = enabled
        if passcode is not None:
            body["passcode"] = passcode
        if language_code is not None:
            body["languageCode"] = language_code
        if greeting is not None:
            body["greeting"] = greeting
        if greeting_description is not None:
            body["greetingDescription"] = greeting_description
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
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



@app.command("delete")
def delete(
    location_id: str = typer.Argument(help="locationId"),
    voicemail_group_id: str = typer.Argument(help="voicemailGroupId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Voicemail Group for a Location."""
    if not force:
        typer.confirm(f"Delete {voicemail_group_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/{voicemail_group_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {voicemail_group_id}")



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    passcode: str = typer.Option(None, "--passcode", help=""),
    language_code: str = typer.Option(None, "--language-code", help=""),
    phone_number: str = typer.Option(None, "--phone-number", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Voicemail Group for a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if extension is not None:
            body["extension"] = extension
        if passcode is not None:
            body["passcode"] = passcode
        if language_code is not None:
            body["languageCode"] = language_code
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
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



@app.command("list-available-numbers")
def list_available_numbers(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Voicemail Group Fax Message Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/faxMessage/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
    items = result.get("availableNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers")
def list_available_numbers(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Voicemail Group Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
    items = result.get("availableNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-available-numbers")
def list_available_numbers(
    location_id: str = typer.Argument(help="locationId"),
    max: str = typer.Option(None, "--max", help="Limit the number of phone numbers returned to this maximum c"),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching phone"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get VoicePortal Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicePortal/availableNumbers"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
    items = result.get("availableNumbers", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


