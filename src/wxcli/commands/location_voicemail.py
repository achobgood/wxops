import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling location-voicemail.")


@app.command("show", short_help="Get Location Voicemail.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Voicemail.\n\n\b\nExample: wxcli location-voicemail show LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemail"
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



_BODY_SKELETON_UPDATE = '{"voicemailTranscriptionEnabled":true}'

@app.command("update", short_help="Update Location Voicemail.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    voicemail_transcription_enabled: bool = typer.Option(None, "--voicemail-transcription-enabled/--no-voicemail-transcription-enabled", help="Set to `true` to enable voicemail transcription."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Location Voicemail.\n\n\b\nExample: wxcli location-voicemail update LOCATION_ID --voicemail-transcription-enabled\n\n\b\nExample --json-body: '{"voicemailTranscriptionEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemail"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if voicemail_transcription_enabled is not None:
            body["voicemailTranscriptionEnabled"] = voicemail_transcription_enabled
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("show-voice-portal", short_help="Get VoicePortal.")
def show_voice_portal(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get VoicePortal.\n\n\b\nExample: wxcli location-voicemail show-voice-portal LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicePortal"
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



_BODY_SKELETON_UPDATE_VOICE_PORTAL = '{"name":"...","languageCode":"...","extension":"...","phoneNumber":"...","firstName":"...","lastName":"...","passcode":{"newPasscode":"...","confirmPasscode":"..."},"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("update-voice-portal", short_help="Update VoicePortal.")
def update_voice_portal(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="Voice Portal Name."),
    language_code: str = typer.Option(None, "--language-code", help="Language code for voicemail group audio announcement."),
    extension: str = typer.Option(None, "--extension", help="Extension of incoming call."),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone Number of incoming call."),
    first_name: str = typer.Option(None, "--first-name", help="Caller ID First Name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Caller ID Last Name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name functions. To clear the `dialByName`, the attribute must be set to null or empty string. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update VoicePortal.\n\n\b\nExample: wxcli location-voicemail update-voice-portal LOCATION_ID\n\n\b\nExample --json-body: '{"name":"...","languageCode":"...","extension":"...","phoneNumber":"...","firstName":"...","lastName":"...","passcode":{"newPasscode":"...","confirmPasscode":"..."},"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VOICE_PORTAL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicePortal"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("show-passcode-rules", short_help="Get VoicePortal Passcode Rule.")
def show_passcode_rules(
    location_id: str = typer.Argument(help="from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get VoicePortal Passcode Rule.\n\n\b\nExample: wxcli location-voicemail show-passcode-rules LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicePortal/passcodeRules"
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



@app.command("list", short_help="List VoicemailGroup.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Location to which the voicemail group belongs."),
    name: str = typer.Option(None, "--name", help="Search (Contains) based on voicemail group name"),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number or extension"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
            result = list(api.session.follow_pagination(url=url, params=params, item_key="voicemailGroups"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("voicemailGroups", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Location Name', 'locationName'), ('Location ID', 'locationId'), ('Extension', 'extension')], limit=limit)



@app.command("show-voicemail-groups", short_help="Get Location Voicemail Group.")
def show_voicemail_groups(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    voicemail_group_id: str = typer.Argument(help="Webex VOICEMAIL_GROUP id, from: wxcli location-voicemail list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Voicemail Group.\n\n\b\nExample: wxcli location-voicemail show-voicemail-groups LOCATION_ID VOICEMAIL_GROUP_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/{voicemail_group_id}"
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



_BODY_SKELETON_UPDATE_VOICEMAIL_GROUPS = '{"name":"...","phoneNumber":"...","extension":0,"firstName":"...","lastName":"...","enabled":true,"passcode":0,"languageCode":"...","greeting":"DEFAULT","greetingDescription":"...","messageStorage":{"storageType":"INTERNAL","externalEmail":"..."},"notifications":{"enabled":true,"destination":"..."},"faxMessage":{"enabled":true,"phoneNumber":"...","extension":0},"transferToNumber":{"enabled":true,"destination":"..."},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("update-voicemail-groups", short_help="Modify Location Voicemail Group.")
def update_voicemail_groups(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    voicemail_group_id: str = typer.Argument(help="Webex VOICEMAIL_GROUP id, from: wxcli location-voicemail list"),
    name: str = typer.Option(None, "--name", help="Set the name of the voicemail group."),
    phone_number: str = typer.Option(None, "--phone-number", help="Set voicemail group phone number."),
    extension: str = typer.Option(None, "--extension", help="Set unique voicemail group extension number."),
    first_name: str = typer.Option(None, "--first-name", help="Set the voicemail group caller ID first name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Set the voicemail group called ID last name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Set to `true` to enable the voicemail group."),
    passcode: str = typer.Option(None, "--passcode", help="Set passcode to access voicemail group when calling."),
    language_code: str = typer.Option(None, "--language-code", help="Language code for the voicemail group audio announcement."),
    greeting: str = typer.Option(None, "--greeting", help="Choices: DEFAULT, CUSTOM"),
    greeting_description: str = typer.Option(None, "--greeting-description", help="CUSTOM greeting for previously uploaded."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name functions. To clear the `dialByName`, the attribute must be set to null or empty string. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Location Voicemail Group.\n\n\b\nExample: wxcli location-voicemail update-voicemail-groups LOCATION_ID VOICEMAIL_GROUP_ID\n\n\b\nExample --json-body: '{"name":"...","phoneNumber":"...","extension":0,"firstName":"...","lastName":"...","enabled":true,"passcode":0,"languageCode":"...","greeting":"DEFAULT","greetingDescription":"...","messageStorage":{"storageType":"INTERNAL","externalEmail":"..."},"notifications":{"enabled":true,"destination":"..."},"faxMessage":{"enabled":true,"phoneNumber":"...","extension":0},"transferToNumber":{"enabled":true,"destination":"..."},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VOICEMAIL_GROUPS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/{voicemail_group_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": voicemail_group_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Voicemail Group for a Location.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    voicemail_group_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli location-voicemail list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Voicemail Group for a Location.\n\n\b\nExample: wxcli location-voicemail delete LOCATION_ID VOICEMAIL_GROUP_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {voicemail_group_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/{voicemail_group_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {voicemail_group_id}")
    else:
        emit({"status": "deleted", "id": voicemail_group_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"name":"...","extension":0,"passcode":0,"languageCode":"...","messageStorage":{"storageType":"INTERNAL","externalEmail":"..."},"notifications":{"enabled":true,"destination":"..."},"faxMessage":{"enabled":true,"phoneNumber":"...","extension":0},"transferToNumber":{"enabled":true,"destination":"..."},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"phoneNumber":"...","firstName":"...","lastName":"...","directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("create", short_help="Create a new Voicemail Group for a Location.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="(required) Set name to create new voicemail group for a particular location for a customer."),
    phone_number: str = typer.Option(None, "--phone-number", help="Set voicemail group phone number for this particular location."),
    extension: str = typer.Option(None, "--extension", help="(required) Set unique voicemail group extension number for this particular location."),
    first_name: str = typer.Option(None, "--first-name", help="Set voicemail group caller ID first name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Set voicemail group called ID last name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    passcode: str = typer.Option(None, "--passcode", help="(required) Set passcode to access voicemail group when calling."),
    language_code: str = typer.Option(None, "--language-code", help="(required) Language code for voicemail group audio announcement."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="The name to be used for dial by name functions. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Voicemail Group for a Location.\n\n\b\nExample: wxcli location-voicemail create LOCATION_ID --json-body '{"name":"...","extension":0,"passcode":0,"languageCode":"...","messageStorage":{"storageType":"INTERNAL"},"notifications":{"enabled":true},"faxMessage":{"enabled":true},"transferToNumber":{"enabled":true},"emailCopyOfMessage":{"enabled":true}}'\n\n\b\nExample --json-body: '{"name":"...","extension":0,"passcode":0,"languageCode":"...","messageStorage":{"storageType":"INTERNAL","externalEmail":"..."},"notifications":{"enabled":true,"destination":"..."},"faxMessage":{"enabled":true,"phoneNumber":"...","extension":0},"transferToNumber":{"enabled":true,"destination":"..."},"emailCopyOfMessage":{"enabled":true,"emailId":"..."},"phoneNumber":"...","firstName":"...","lastName":"...","directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
        if passcode is not None:
            body["passcode"] = passcode
        if language_code is not None:
            body["languageCode"] = language_code
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        _missing = [f for f in ['name', 'extension', 'passcode', 'languageCode'] if f not in body or body[f] is None]
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



@app.command("list-available-numbers-fax-message", short_help="Get Voicemail Group Fax Message Available Phone Numbers.")
def list_available_numbers_fax_message(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Voicemail Group Fax Message Available Phone Numbers.\n\n\b\nExample: wxcli location-voicemail list-available-numbers-fax-message LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/faxMessage/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber'), ('Telephony Type', 'telephonyType')], limit=limit)



@app.command("list-available-numbers-voicemail-groups", short_help="Get Voicemail Group Available Phone Numbers.")
def list_available_numbers_voicemail_groups(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Voicemail Group Available Phone Numbers.\n\n\b\nExample: wxcli location-voicemail list-available-numbers-voicemail-groups LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicemailGroups/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber'), ('Telephony Type', 'telephonyType')], limit=limit)



@app.command("list-available-numbers-voice-portal", short_help="Get VoicePortal Available Phone Numbers.")
def list_available_numbers_voice_portal(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get VoicePortal Available Phone Numbers.\n\n\b\nExample: wxcli location-voicemail list-available-numbers-voice-portal LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/voicePortal/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber'), ('Telephony Type', 'telephonyType')], limit=limit)


