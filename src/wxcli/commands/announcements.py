import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling announcements.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Choices: all, locations, Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzMxMTYx"),
    order: str = typer.Option(None, "--order", help="Sort the list according to fileName or fileSize. The default"),
    file_name: str = typer.Option(None, "--file-name", help="Return the list of announcements with the given fileName."),
    file_type: str = typer.Option(None, "--file-type", help="Return the list of announcement files for this fileType."),
    media_file_type: str = typer.Option(None, "--media-file-type", help="Return the list of announcement files for this mediaFileType"),
    name: str = typer.Option(None, "--name", help="Return the list of announcement files for this announcement"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch list of announcement greetings on location and organization level."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if order is not None:
        params["order"] = order
    if file_name is not None:
        params["fileName"] = file_name
    if file_type is not None:
        params["fileType"] = file_type
    if media_file_type is not None:
        params["mediaFileType"] = media_file_type
    if name is not None:
        params["name"] = name
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("announcements", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="announcements"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    name: str = typer.Option(None, "--name", help="(required) Name of the announcement."),
    file_uri: str = typer.Option(None, "--file-uri", help="(required) URI of the announcement file."),
    file_name: str = typer.Option(None, "--file-name", help="(required) File name of the announcement."),
    is_text_to_speech: bool = typer.Option(None, "--is-text-to-speech/--no-is-text-to-speech", help="(required) Indicates whether the announcement is text-to-speech."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Upload a binary announcement greeting at organization level."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if file_uri is not None:
            body["fileUri"] = file_uri
        if file_name is not None:
            body["fileName"] = file_name
        if is_text_to_speech is not None:
            body["isTextToSpeech"] = is_text_to_speech
        _missing = [f for f in ['name', 'fileUri', 'fileName', 'isTextToSpeech'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch repository usage for announcements for an organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/usage"
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



@app.command("show-announcements-config")
def show_announcements_config(
    announcement_id: str = typer.Argument(help="announcementId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch details of a binary announcement greeting at the organization level."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/{announcement_id}"
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
    announcement_id: str = typer.Argument(help="announcementId"),
    name: str = typer.Option(None, "--name", help="Name of the announcement."),
    file_uri: str = typer.Option(None, "--file-uri", help="URI of the announcement file."),
    file_name: str = typer.Option(None, "--file-name", help="File name of the announcement."),
    is_text_to_speech: bool = typer.Option(None, "--is-text-to-speech/--no-is-text-to-speech", help="Indicates whether the announcement is text-to-speech."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a binary announcement greeting at organization level."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/{announcement_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if file_uri is not None:
            body["fileUri"] = file_uri
        if file_name is not None:
            body["fileName"] = file_name
        if is_text_to_speech is not None:
            body["isTextToSpeech"] = is_text_to_speech
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    announcement_id: str = typer.Argument(help="announcementId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an announcement greeting of the organization."""
    if not force:
        typer.confirm(f"Delete {announcement_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/{announcement_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {announcement_id}")



@app.command("create-announcements")
def create_announcements(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) Name of the announcement."),
    file_uri: str = typer.Option(None, "--file-uri", help="(required) URI of the announcement file."),
    file_name: str = typer.Option(None, "--file-name", help="(required) File name of the announcement."),
    is_text_to_speech: bool = typer.Option(None, "--is-text-to-speech/--no-is-text-to-speech", help="(required) Indicates whether the announcement is text-to-speech."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Upload a binary announcement greeting at the location level."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if file_uri is not None:
            body["fileUri"] = file_uri
        if file_name is not None:
            body["fileName"] = file_name
        if is_text_to_speech is not None:
            body["isTextToSpeech"] = is_text_to_speech
        _missing = [f for f in ['name', 'fileUri', 'fileName', 'isTextToSpeech'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-usage-announcements")
def show_usage_announcements(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch repository usage for announcements in a location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements/usage"
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



@app.command("show-announcements-locations")
def show_announcements_locations(
    location_id: str = typer.Argument(help="locationId"),
    announcement_id: str = typer.Argument(help="announcementId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch details of a binary announcement greeting at location level."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements/{announcement_id}"
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



@app.command("update-announcements")
def update_announcements(
    location_id: str = typer.Argument(help="locationId"),
    announcement_id: str = typer.Argument(help="announcementId"),
    name: str = typer.Option(None, "--name", help="Name of the announcement."),
    file_uri: str = typer.Option(None, "--file-uri", help="URI of the announcement file."),
    file_name: str = typer.Option(None, "--file-name", help="File name of the announcement."),
    is_text_to_speech: bool = typer.Option(None, "--is-text-to-speech/--no-is-text-to-speech", help="Indicates whether the announcement is text-to-speech."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a binary announcement greeting at location level."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements/{announcement_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if file_uri is not None:
            body["fileUri"] = file_uri
        if file_name is not None:
            body["fileName"] = file_name
        if is_text_to_speech is not None:
            body["isTextToSpeech"] = is_text_to_speech
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-announcements")
def delete_announcements(
    location_id: str = typer.Argument(help="locationId"),
    announcement_id: str = typer.Argument(help="announcementId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an announcement greeting in a location."""
    if not force:
        typer.confirm(f"Delete {announcement_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements/{announcement_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {announcement_id}")



@app.command("generate-a-text")
def generate_a_text(
    voice: str = typer.Option(None, "--voice", help="The voice ID used to generate the audio prompt. Use the List"),
    text: str = typer.Option(None, "--text", help="The text to convert to speech."),
    language_code: str = typer.Option(None, "--language-code", help="The language code used to generate the audio prompt. Use the"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate a Text-to-Speech Prompt."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/textToSpeech/actions/generate/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if voice is not None:
            body["voice"] = voice
        if text is not None:
            body["text"] = text
        if language_code is not None:
            body["languageCode"] = language_code
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    print_json(result)



@app.command("show-usage-text-to-speech")
def show_usage_text_to_speech(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Text-to-Speech Usage."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/textToSpeech/usage"
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



@app.command("show-text-to-speech")
def show_text_to_speech(
    tts_id: str = typer.Argument(help="ttsId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Text-to-Speech Generation Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/textToSpeech/{tts_id}"
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



@app.command("list-voices")
def list_voices(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Text-to-Speech Voices."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/textToSpeech/voices"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("voices", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


