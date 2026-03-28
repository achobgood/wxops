import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling tracking-codes.")


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
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Name', 'name'), ('Site URL', 'siteUrl'), ('Service', 'service')], limit=limit)



@app.command("create")
def create(
    input_mode: str = typer.Option(None, "--input-mode", help=""),
    host_profile_code: str = typer.Option(None, "--host-profile-code", help=""),
    name: str = typer.Option(None, "--name", help=""),
    site_url: str = typer.Option(None, "--site-url", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Tracking Code\n\nExample --json-body:\n  '{"inputMode":"...","hostProfileCode":"...","name":"...","scheduleStartCodes":[{"service":"...","type":"..."}],"options":[{"defaultValue":"...","value":"..."}],"siteUrl":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if input_mode is not None:
            body["inputMode"] = input_mode
        if host_profile_code is not None:
            body["hostProfileCode"] = host_profile_code
        if name is not None:
            body["name"] = name
        if site_url is not None:
            body["siteUrl"] = site_url
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



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
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("trackingCodes", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Name', 'name'), ('Site URL', 'siteUrl'), ('Service', 'service')], limit=limit)



@app.command("update")
def update(
    email: str = typer.Option(None, "--email", help=""),
    site_url: str = typer.Option(None, "--site-url", help=""),
    person_id: str = typer.Option(None, "--person-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update User Tracking Codes\n\nExample --json-body:\n  '{"trackingCodes":[{"name":"...","value":"..."}],"email":"...","siteUrl":"...","personId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/userconfig/trackingCodes"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if email is not None:
            body["email"] = email
        if site_url is not None:
            body["siteUrl"] = site_url
        if person_id is not None:
            body["personId"] = person_id
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



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
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-tracking-codes")
def update_tracking_codes(
    tracking_code_id: str = typer.Argument(help="trackingCodeId"),
    input_mode: str = typer.Option(None, "--input-mode", help=""),
    host_profile_code: str = typer.Option(None, "--host-profile-code", help=""),
    name: str = typer.Option(None, "--name", help=""),
    site_url: str = typer.Option(None, "--site-url", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Tracking Code\n\nExample --json-body:\n  '{"inputMode":"...","hostProfileCode":"...","name":"...","scheduleStartCodes":[{"service":"...","type":"..."}],"options":[{"defaultValue":"...","value":"..."}],"siteUrl":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/trackingCodes/{tracking_code_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if input_mode is not None:
            body["inputMode"] = input_mode
        if host_profile_code is not None:
            body["hostProfileCode"] = host_profile_code
        if name is not None:
            body["name"] = name
        if site_url is not None:
            body["siteUrl"] = site_url
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    tracking_code_id: str = typer.Argument(help="trackingCodeId"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API deletes the trackin"),
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
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {tracking_code_id}")


