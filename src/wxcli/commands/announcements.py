import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling announcements.")


@app.command("list", short_help="Fetch list of announcement greetings on location and organization level.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Choices: all, locations, Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzMxMTYx"),
    order: str = typer.Option(None, "--order", help="Sort the list according to fileName or fileSize. The default sort will be in Ascending order."),
    file_name: str = typer.Option(None, "--file-name", help="Return the list of announcements with the given fileName."),
    file_type: str = typer.Option(None, "--file-type", help="Return the list of announcement files for this fileType."),
    media_file_type: str = typer.Option(None, "--media-file-type", help="Return the list of announcement files for this mediaFileType."),
    name: str = typer.Option(None, "--name", help="Return the list of announcement files for this announcement label."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("announcements", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="announcements"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('File Name', 'fileName'), ('File Size', 'fileSize'), ('Media File Type', 'mediaFileType')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","fileUri":"...","fileName":"...","isTextToSpeech":true}'

@app.command("create", short_help="Upload a binary announcement greeting at organization level.")
def create(
    name: str = typer.Option(None, "--name", help="(required) Name of the announcement."),
    file_uri: str = typer.Option(None, "--file-uri", help="(required) URI of the announcement file."),
    file_name: str = typer.Option(None, "--file-name", help="(required) File name of the announcement."),
    is_text_to_speech: bool = typer.Option(None, "--is-text-to-speech/--no-is-text-to-speech", help="(required) Indicates whether the announcement is text-to-speech."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Upload a binary announcement greeting at organization level.\n\n\b\nExample: wxcli announcements create --name NAME --file-uri FILE_URI --file-name FILE_NAME --is-text-to-speech\n\n\b\nExample --json-body: '{"name":"...","fileUri":"...","fileName":"...","isTextToSpeech":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements"
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



@app.command("show", short_help="Fetch repository usage for announcements for an organization.")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-announcements-config", short_help="Fetch details of a binary announcement greeting at the organization level.")
def show_announcements_config(
    announcement_id: str = typer.Argument(help="Webex ANNOUNCEMENT id, from: wxcli announcements list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch details of a binary announcement greeting at the organization level.\n\n\b\nExample: wxcli announcements show-announcements-config ANNOUNCEMENT_ID"""
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","fileUri":"...","fileName":"...","isTextToSpeech":true}'

@app.command("update", short_help="Modify a binary announcement greeting at organization level.")
def update(
    announcement_id: str = typer.Argument(help="Webex ANNOUNCEMENT id, from: wxcli announcements list"),
    name: str = typer.Option(None, "--name", help="Name of the announcement."),
    file_uri: str = typer.Option(None, "--file-uri", help="URI of the announcement file."),
    file_name: str = typer.Option(None, "--file-name", help="File name of the announcement."),
    is_text_to_speech: bool = typer.Option(None, "--is-text-to-speech/--no-is-text-to-speech", help="Indicates whether the announcement is text-to-speech."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a binary announcement greeting at organization level.\n\n\b\nExample: wxcli announcements update ANNOUNCEMENT_ID --name NAME --file-uri FILE_URI --file-name FILE_NAME --is-text-to-speech\n\n\b\nExample --json-body: '{"name":"...","fileUri":"...","fileName":"...","isTextToSpeech":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/{announcement_id}"
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": announcement_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete an announcement greeting of the organization.")
def delete(
    announcement_id: str = typer.Argument(help="Webex ANNOUNCEMENT id, from: wxcli announcements list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an announcement greeting of the organization.\n\n\b\nExample: wxcli announcements delete ANNOUNCEMENT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {announcement_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/announcements/{announcement_id}"
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
        typer.echo(f"Deleted: {announcement_id}")
    else:
        emit({"status": "deleted", "id": announcement_id}, output=output, fields=fields)



@app.command("show-file-uri-announcements", short_help="Get Announcement File URI.")
def show_file_uri_announcements(
    announcement_id: str = typer.Argument(help="Webex ANNOUNCEMENT id, from: wxcli announcements list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Announcement File URI.\n\n\b\nExample: wxcli announcements show-file-uri-announcements ANNOUNCEMENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/{announcement_id}/fileUri"
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



@app.command("generate-upload-url", short_help="Generate Upload URL.")
def generate_upload_url(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate Upload URL."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/uploadUrls/actions/generate/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_ANNOUNCEMENTS = '{"name":"...","fileUri":"...","fileName":"...","isTextToSpeech":true}'

@app.command("create-announcements", short_help="Upload a binary announcement greeting at the location level.")
def create_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="(required) Name of the announcement."),
    file_uri: str = typer.Option(None, "--file-uri", help="(required) URI of the announcement file."),
    file_name: str = typer.Option(None, "--file-name", help="(required) File name of the announcement."),
    is_text_to_speech: bool = typer.Option(None, "--is-text-to-speech/--no-is-text-to-speech", help="(required) Indicates whether the announcement is text-to-speech."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Upload a binary announcement greeting at the location level.\n\n\b\nExample: wxcli announcements create-announcements LOCATION_ID --name NAME --file-uri FILE_URI --file-name FILE_NAME --is-text-to-speech\n\n\b\nExample --json-body: '{"name":"...","fileUri":"...","fileName":"...","isTextToSpeech":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ANNOUNCEMENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements"
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



@app.command("show-usage-announcements", short_help="Fetch repository usage for announcements in a location.")
def show_usage_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch repository usage for announcements in a location.\n\n\b\nExample: wxcli announcements show-usage-announcements LOCATION_ID"""
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-announcements-locations", short_help="Fetch details of a binary announcement greeting at location level.")
def show_announcements_locations(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    announcement_id: str = typer.Argument(help="Webex ANNOUNCEMENT id, from: wxcli announcements list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch details of a binary announcement greeting at location level.\n\n\b\nExample: wxcli announcements show-announcements-locations LOCATION_ID ANNOUNCEMENT_ID"""
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ANNOUNCEMENTS = '{"name":"...","fileUri":"...","fileName":"...","isTextToSpeech":true}'

@app.command("update-announcements", short_help="Modify a binary announcement greeting at location level.")
def update_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    announcement_id: str = typer.Argument(help="Webex ANNOUNCEMENT id, from: wxcli announcements list"),
    name: str = typer.Option(None, "--name", help="Name of the announcement."),
    file_uri: str = typer.Option(None, "--file-uri", help="URI of the announcement file."),
    file_name: str = typer.Option(None, "--file-name", help="File name of the announcement."),
    is_text_to_speech: bool = typer.Option(None, "--is-text-to-speech/--no-is-text-to-speech", help="Indicates whether the announcement is text-to-speech."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a binary announcement greeting at location level.\n\n\b\nExample: wxcli announcements update-announcements LOCATION_ID ANNOUNCEMENT_ID --name NAME --file-uri FILE_URI --file-name FILE_NAME --is-text-to-speech\n\n\b\nExample --json-body: '{"name":"...","fileUri":"...","fileName":"...","isTextToSpeech":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ANNOUNCEMENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements/{announcement_id}"
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": announcement_id}, output=output, fields=fields)



@app.command("delete-announcements", short_help="Delete an announcement greeting in a location.")
def delete_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    announcement_id: str = typer.Argument(help="Webex ANNOUNCEMENT id, from: wxcli announcements list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an announcement greeting in a location.\n\n\b\nExample: wxcli announcements delete-announcements LOCATION_ID ANNOUNCEMENT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {announcement_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements/{announcement_id}"
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
        typer.echo(f"Deleted: {announcement_id}")
    else:
        emit({"status": "deleted", "id": announcement_id}, output=output, fields=fields)



@app.command("show-file-uri-announcements-1", short_help="Get Location Announcement File URI.")
def show_file_uri_announcements_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    announcement_id: str = typer.Argument(help="Webex ANNOUNCEMENT id, from: wxcli announcements list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Announcement File URI.\n\n\b\nExample: wxcli announcements show-file-uri-announcements-1 LOCATION_ID ANNOUNCEMENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/announcements/{announcement_id}/fileUri"
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



@app.command("show-urls", short_help="Get Media Download URL.")
def show_urls(
    s3_path: str = typer.Argument(help="s3Path"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Media Download URL.\n\n\b\nExample: wxcli announcements show-urls S3_PATH"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/media/urls/{s3_path}"
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



_BODY_SKELETON_TTS_GENERATE = '{"voice":"...","text":"...","languageCode":"..."}'

@app.command("generate-a-text", hidden=True)
@app.command("tts-generate", short_help="Generate a Text-to-Speech Prompt.")
def tts_generate(
    voice: str = typer.Option(None, "--voice", help="The voice ID used to generate the audio prompt. Use the List Text-to-Speech Voices API to retrieve available voices."),
    text: str = typer.Option(None, "--text", help="The text to convert to speech."),
    language_code: str = typer.Option(None, "--language-code", help="The language code used to generate the audio prompt. Use the Read the List of Announcement Languages API to retrieve supported language codes."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate a Text-to-Speech Prompt.\n\n\b\nExample: wxcli announcements tts-generate --voice VOICE --text TEXT --language-code LANGUAGE_CODE\n\n\b\nExample --json-body: '{"voice":"...","text":"...","languageCode":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_TTS_GENERATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/textToSpeech/actions/generate/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-usage-text-to-speech", hidden=True)
@app.command("tts-usage", short_help="Get Text-to-Speech Usage.")
def tts_usage(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-text-to-speech", hidden=True)
@app.command("tts-status", short_help="Get Text-to-Speech Generation Status.")
def tts_status(
    tts_id: str = typer.Argument(help="Webex TEXT_TO_SPEECH id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Text-to-Speech Generation Status.\n\n\b\nExample: wxcli announcements tts-status TTS_ID"""
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-voices", hidden=True)
@app.command("tts-voices", short_help="List Text-to-Speech Voices.")
def tts_voices(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("voices", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Label', 'label')], limit=limit)


