import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-tracking-codes.")


@app.command("list", short_help="List Tracking Codes.")
def cmd_list(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API retrieves the tracking code from. If not specified, the API retrieves the tracking code from the user's preferred site. All available Webex sites and preferred sites of a user can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list)..."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Tracking Codes."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Site URL', 'siteUrl')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","siteUrl":"...","options":[{"value":"...","defaultValue":"..."}],"inputMode":"text","hostProfileCode":"optional","scheduleStartCodes":[{"service":"...","type":"..."}]}'

@app.command("create", short_help="Create a Tracking Code.")
def create(
    name: str = typer.Option(None, "--name", help="(required) Name for tracking code. The name cannot be empty and the maximum size is 120 characters."),
    site_url: str = typer.Option(None, "--site-url", help="(required) Site URL for the tracking code."),
    input_mode: str = typer.Option(None, "--input-mode", help="(required) Choices: text, select, editableSelect, hostProfileSelect"),
    host_profile_code: str = typer.Option(None, "--host-profile-code", help="(required) Choices: optional, required, adminSet, notUsed"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Tracking Code.\n\n\b\nExample: wxcli meeting-tracking-codes create --name NAME --site-url SITE_URL --input-mode text --host-profile-code optional\n\n\b\nExample --json-body: '{"name":"...","siteUrl":"...","options":[{"value":"...","defaultValue":"..."}],"inputMode":"text","hostProfileCode":"optional","scheduleStartCodes":[{"service":"...","type":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if site_url is not None:
            body["siteUrl"] = site_url
        if input_mode is not None:
            body["inputMode"] = input_mode
        if host_profile_code is not None:
            body["hostProfileCode"] = host_profile_code
        _missing = [f for f in ['name', 'siteUrl', 'inputMode', 'hostProfileCode'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get a Tracking Code.")
def show(
    tracking_code_id: str = typer.Argument(help="from: wxcli meeting-tracking-codes list"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API retrieves the tracking code from. If not specified, the API retrieves the tracking code from the user's preferred site. All available Webex sites and the preferred sites of a user can be retrieved by the [Get Site..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Tracking Code.\n\n\b\nExample: wxcli meeting-tracking-codes show TRACKING_CODE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes/{tracking_code_id}"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","siteUrl":"...","options":[{"value":"...","defaultValue":"..."}],"inputMode":"text","hostProfileCode":"optional","scheduleStartCodes":[{"service":"...","type":"..."}]}'

@app.command("update", short_help="Update a Tracking Code.")
def update(
    tracking_code_id: str = typer.Argument(help="from: wxcli meeting-tracking-codes list"),
    name: str = typer.Option(None, "--name", help="Name for tracking code. The name cannot be empty and the maximum size is 120 characters."),
    site_url: str = typer.Option(None, "--site-url", help="Site URL for the tracking code."),
    input_mode: str = typer.Option(None, "--input-mode", help="Choices: text, select, editableSelect, hostProfileSelect"),
    host_profile_code: str = typer.Option(None, "--host-profile-code", help="Choices: optional, required, adminSet, notUsed"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Tracking Code.\n\n\b\nExample: wxcli meeting-tracking-codes update TRACKING_CODE_ID --name NAME --site-url SITE_URL --input-mode text --host-profile-code optional\n\n\b\nExample --json-body: '{"name":"...","siteUrl":"...","options":[{"value":"...","defaultValue":"..."}],"inputMode":"text","hostProfileCode":"optional","scheduleStartCodes":[{"service":"...","type":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes/{tracking_code_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if site_url is not None:
            body["siteUrl"] = site_url
        if input_mode is not None:
            body["inputMode"] = input_mode
        if host_profile_code is not None:
            body["hostProfileCode"] = host_profile_code
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": tracking_code_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Tracking Code.")
def delete(
    tracking_code_id: str = typer.Argument(help="from: wxcli meeting-tracking-codes list"),
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site from which the API deletes the tracking code. All available Webex sites and preferred sites of a user can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Tracking Code.\n\n\b\nExample: wxcli meeting-tracking-codes delete TRACKING_CODE_ID --site-url SITE_URL"""
    if not force:
        typer.confirm(f"Delete {tracking_code_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes/{tracking_code_id}"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {tracking_code_id}")
    else:
        emit({"status": "deleted", "id": tracking_code_id}, output=output, fields=fields)



@app.command("list-tracking-codes", short_help="Get User Tracking Codes.")
def list_tracking_codes(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API retrieves the tracking code. If not specified, the API retrieves the tracking code from the user's preferred site. All available Webex sites and preferred sites of a user can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list)..."),
    person_id: str = typer.Option(None, "--person-id", help="Unique identifier for the user whose tracking codes are being retrieved. The admin user can specify the `personId` of a user on a site they manage and the API returns details for the user's tracking codes. At least one parameter of `personId` or `email` is required."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get User Tracking Codes."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/userconfig/trackingCodes"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    if person_id is not None:
        params["personId"] = person_id
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
    items = result.get("trackingCodes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Value', 'value')], limit=limit)



_BODY_SKELETON_UPDATE_TRACKING_CODES = '{"siteUrl":"...","personId":"...","email":"...","trackingCodes":[{"name":"...","value":"..."}]}'

@app.command("update-tracking-codes", short_help="Update User Tracking Codes.")
def update_tracking_codes(
    site_url: str = typer.Option(None, "--site-url", help="Site URL for the tracking code."),
    person_id: str = typer.Option(None, "--person-id", help="Unique identifier for the user. At least one parameter of `personId` or `email` is required. `personId` must precede `email` if both are specified."),
    email: str = typer.Option(None, "--email", help="Email address for the user. At least one parameter of `personId` or `email` is required. `personId` must precede `email` if both are specified."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User Tracking Codes.\n\n\b\nExample: wxcli meeting-tracking-codes update-tracking-codes --site-url SITE_URL\n\n\b\nExample --json-body: '{"siteUrl":"...","personId":"...","email":"...","trackingCodes":[{"name":"...","value":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_TRACKING_CODES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/userconfig/trackingCodes"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
        if person_id is not None:
            body["personId"] = person_id
        if email is not None:
            body["email"] = email
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)


