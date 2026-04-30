import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-tracking-codes.")


@app.command("list")
def cmd_list(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API retrieves the tracking c"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Name', 'name'), ('Site URL', 'siteUrl'), ('Service', 'service')], limit=limit)



@app.command("create")
def create(
    name: str = typer.Option(None, "--name", help="(required) Name for tracking code. The name cannot be empty and the max"),
    site_url: str = typer.Option(None, "--site-url", help="(required) Site URL for the tracking code."),
    input_mode: str = typer.Option(None, "--input-mode", help="(required) Choices: text, select, editableSelect, hostProfileSelect"),
    host_profile_code: str = typer.Option(None, "--host-profile-code", help="(required) Choices: optional, required, adminSet, notUsed"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Tracking Code\n\nExample --json-body:\n  '{"name":"...","siteUrl":"...","options":[{"value":"...","defaultValue":"..."}],"inputMode":"text","hostProfileCode":"optional","scheduleStartCodes":[{"service":"...","type":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes"
    if json_body:
        body = json.loads(json_body)
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
    tracking_code_id: str = typer.Argument(help="trackingCodeId"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API retrieves the tracking c"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Tracking Code."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes/{tracking_code_id}"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
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
    name: str = typer.Option(None, "--name", help="Name for tracking code. The name cannot be empty and the max"),
    site_url: str = typer.Option(None, "--site-url", help="Site URL for the tracking code."),
    input_mode: str = typer.Option(None, "--input-mode", help="Choices: text, select, editableSelect, hostProfileSelect"),
    host_profile_code: str = typer.Option(None, "--host-profile-code", help="Choices: optional, required, adminSet, notUsed"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Tracking Code\n\nExample --json-body:\n  '{"name":"...","siteUrl":"...","options":[{"value":"...","defaultValue":"..."}],"inputMode":"text","hostProfileCode":"optional","scheduleStartCodes":[{"service":"...","type":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes/{trackingCodeId}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    tracking_code_id: str = typer.Argument(help="trackingCodeId"),
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site from which the API deletes the trackin"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Tracking Code."""
    if not force:
        typer.confirm(f"Delete {tracking_code_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes/{tracking_code_id}"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {tracking_code_id}")



@app.command("list-tracking-codes")
def list_tracking_codes(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API retrieves the track"),
    person_id: str = typer.Option(None, "--person-id", help="Unique identifier for the user whose tracking codes are bein"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("trackingCodes", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Name', 'name'), ('Site URL', 'siteUrl'), ('Service', 'service')], limit=limit)



@app.command("update-tracking-codes")
def update_tracking_codes(
    site_url: str = typer.Option(None, "--site-url", help="Site URL for the tracking code."),
    person_id: str = typer.Option(None, "--person-id", help="Unique identifier for the user. At least one parameter of `p"),
    email: str = typer.Option(None, "--email", help="Email address for the user. At least one parameter of `perso"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User Tracking Codes\n\nExample --json-body:\n  '{"siteUrl":"...","personId":"...","email":"...","trackingCodes":[{"name":"...","value":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/userconfig/trackingCodes"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")


