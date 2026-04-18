import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meetings.")


@app.command("show")
def show(
    template_id: str = typer.Argument(help="templateId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Template."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/templates/{template_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("list")
def cmd_list(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API retrieves the tracking c"),
    service: str = typer.Option(None, "--service", help="Service for schedule or sign-up pages."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Tracking Codes."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/trackingCodes"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    if service is not None:
        params["service"] = service
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("show-controls")
def show_controls(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the meeting. Does not support meeting"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Control Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/controls"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("update")
def update(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the meeting. Does not support meeting"),
    locked: str = typer.Option(None, "--locked", help=""),
    recording_started: str = typer.Option(None, "--recording-started", help=""),
    recording_paused: str = typer.Option(None, "--recording-paused", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Control Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/controls"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if locked is not None:
            body["locked"] = locked
        if recording_started is not None:
            body["recordingStarted"] = recording_started
        if recording_paused is not None:
            body["recordingPaused"] = recording_paused
    try:
        result = api.session.rest_put(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-session-types")
def list_session_types(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="Webex site URL to query. If `siteUrl` is not specified, the"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Session Types."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/sessionTypes"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("show-session-types")
def show_session_types(
    session_type_id: str = typer.Argument(help="sessionTypeId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the user. This parameter is only used if t"),
    site_url: str = typer.Option(None, "--site-url", help="Webex site URL to query. If `siteUrl` is not specified, the"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Session Type."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/sessionTypes/{session_type_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("list-registration")
def list_registration(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get registration form for a meeting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registration"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("rules", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("update-registration")
def update_registration(
    meeting_id: str = typer.Argument(help="meetingId"),
    require_company_name: str = typer.Option(None, "--require-company-name", help=""),
    require_address1: str = typer.Option(None, "--require-address1", help=""),
    require_address2: str = typer.Option(None, "--require-address2", help=""),
    require_city: str = typer.Option(None, "--require-city", help=""),
    host_email: str = typer.Option(None, "--host-email", help=""),
    require_zip_code: str = typer.Option(None, "--require-zip-code", help=""),
    require_country_region: str = typer.Option(None, "--require-country-region", help=""),
    require_work_phone: str = typer.Option(None, "--require-work-phone", help=""),
    require_fax: str = typer.Option(None, "--require-fax", help=""),
    max_register_num: str = typer.Option(None, "--max-register-num", help=""),
    require_state: str = typer.Option(None, "--require-state", help=""),
    auto_accept_request: str = typer.Option(None, "--auto-accept-request", help=""),
    require_first_name: str = typer.Option(None, "--require-first-name", help=""),
    require_last_name: str = typer.Option(None, "--require-last-name", help=""),
    require_email: str = typer.Option(None, "--require-email", help=""),
    require_job_title: str = typer.Option(None, "--require-job-title", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Registration Form\n\nExample --json-body:\n  '{"requireCompanyName":"...","requireAddress1":"...","requireAddress2":"...","requireCity":"...","hostEmail":"...","requireZipCode":"...","requireCountryRegion":"...","requireWorkPhone":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registration"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if require_company_name is not None:
            body["requireCompanyName"] = require_company_name
        if require_address1 is not None:
            body["requireAddress1"] = require_address1
        if require_address2 is not None:
            body["requireAddress2"] = require_address2
        if require_city is not None:
            body["requireCity"] = require_city
        if host_email is not None:
            body["hostEmail"] = host_email
        if require_zip_code is not None:
            body["requireZipCode"] = require_zip_code
        if require_country_region is not None:
            body["requireCountryRegion"] = require_country_region
        if require_work_phone is not None:
            body["requireWorkPhone"] = require_work_phone
        if require_fax is not None:
            body["requireFax"] = require_fax
        if max_register_num is not None:
            body["maxRegisterNum"] = max_register_num
        if require_state is not None:
            body["requireState"] = require_state
        if auto_accept_request is not None:
            body["autoAcceptRequest"] = auto_accept_request
        if require_first_name is not None:
            body["requireFirstName"] = require_first_name
        if require_last_name is not None:
            body["requireLastName"] = require_last_name
        if require_email is not None:
            body["requireEmail"] = require_email
        if require_job_title is not None:
            body["requireJobTitle"] = require_job_title
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    meeting_id: str = typer.Argument(help="meetingId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Meeting Registration Form."""
    if not force:
        typer.confirm(f"Delete {meeting_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registration"
    try:
        api.session.rest_delete(url)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {meeting_id}")



@app.command("list-registrants")
def list_registrants(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    email: str = typer.Option(None, "--email", help="Registrant's email to filter registrants."),
    registration_time_from: str = typer.Option(None, "--registration-time-from", help="The time registrants register a meeting starts from the spec"),
    registration_time_to: str = typer.Option(None, "--registration-time-to", help="The time registrants register a meeting before the specified"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Registrants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if current is not None:
        params["current"] = current
    if email is not None:
        params["email"] = email
    if registration_time_from is not None:
        params["registrationTimeFrom"] = registration_time_from
    if registration_time_to is not None:
        params["registrationTimeTo"] = registration_time_to
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create")
def create(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    last_name: str = typer.Option(None, "--last-name", help=""),
    address1: str = typer.Option(None, "--address1", help=""),
    address2: str = typer.Option(None, "--address2", help=""),
    city: str = typer.Option(None, "--city", help=""),
    zip_code: str = typer.Option(None, "--zip-code", help=""),
    state: str = typer.Option(None, "--state", help=""),
    country_region: str = typer.Option(None, "--country-region", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    job_title: str = typer.Option(None, "--job-title", help=""),
    work_phone: str = typer.Option(None, "--work-phone", help=""),
    fax: str = typer.Option(None, "--fax", help=""),
    company_name: str = typer.Option(None, "--company-name", help=""),
    email: str = typer.Option(None, "--email", help=""),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Register a Meeting Registrant\n\nExample --json-body:\n  '{"lastName":"...","address1":"...","address2":"...","city":"...","customizedQuestions":[{"questionId":"...","answers":"..."}],"zipCode":"...","state":"...","countryRegion":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if last_name is not None:
            body["lastName"] = last_name
        if address1 is not None:
            body["address1"] = address1
        if address2 is not None:
            body["address2"] = address2
        if city is not None:
            body["city"] = city
        if zip_code is not None:
            body["zipCode"] = zip_code
        if state is not None:
            body["state"] = state
        if country_region is not None:
            body["countryRegion"] = country_region
        if first_name is not None:
            body["firstName"] = first_name
        if job_title is not None:
            body["jobTitle"] = job_title
        if work_phone is not None:
            body["workPhone"] = work_phone
        if fax is not None:
            body["fax"] = fax
        if company_name is not None:
            body["companyName"] = company_name
        if email is not None:
            body["email"] = email
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-reassign-host")
def create_reassign_host(
    host_email: str = typer.Option(None, "--host-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reassign Meetings to a New Host\n\nExample --json-body:\n  '{"hostEmail":"...","meetingIds":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/reassignHost"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("list-meetings")
def list_meetings(
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number for the meeting objects being requested. `mee"),
    web_link: str = typer.Option(None, "--web-link", help="URL encoded link to information page for the meeting objects"),
    room_id: str = typer.Option(None, "--room-id", help="Associated Webex space ID for the meeting objects being requ"),
    meeting_series_id: str = typer.Option(None, "--meeting-series-id", help="Unique identifier for the meeting series. The meeting ID of"),
    from_param: str = typer.Option(None, "--from", help="Start date and time (inclusive) for the range for which meet"),
    to: str = typer.Option(None, "--to", help="End date and time (exclusive) for the range for which meetin"),
    meeting_type: str = typer.Option(None, "--meeting-type", help="Meeting type for the meeting objects being requested. This p"),
    state: str = typer.Option(None, "--state", help="Meeting state for the meeting objects being requested. If no"),
    scheduled_type: str = typer.Option(None, "--scheduled-type", help="Scheduled type for the meeting objects being requested."),
    is_modified: str = typer.Option(None, "--is-modified", help="Flag identifying whether a meeting has been modified. Only a"),
    has_chat: str = typer.Option(None, "--has-chat", help="Flag identifying whether a meeting has a chat log. Only appl"),
    has_recording: str = typer.Option(None, "--has-recording", help="Flag identifying meetings which have been recorded. Only app"),
    has_transcription: str = typer.Option(None, "--has-transcription", help="Flag identifying meetings with transcripts. Only applies to"),
    has_summary: str = typer.Option(None, "--has-summary", help="Flag identifying meetings with summaries. Only applies to en"),
    has_closed_caption: str = typer.Option(None, "--has-closed-caption", help="Flag identifying meetings with closed captions. Only applies"),
    has_polls: str = typer.Option(None, "--has-polls", help="Flag identifying meetings with polls. Only applies to ended"),
    has_qa: str = typer.Option(None, "--has-qa", help="Flag identifying meetings with Q&A. Only applies to ended me"),
    has_slido: str = typer.Option(None, "--has-slido", help="Flag identifying meetings with Slido interactions. Only appl"),
    current: str = typer.Option(None, "--current", help="Flag identifying to retrieve the current scheduled meeting o"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meetings from. If"),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key created by an integration application. This par"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meetings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings"
    params = {}
    if meeting_number is not None:
        params["meetingNumber"] = meeting_number
    if web_link is not None:
        params["webLink"] = web_link
    if room_id is not None:
        params["roomId"] = room_id
    if meeting_series_id is not None:
        params["meetingSeriesId"] = meeting_series_id
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if meeting_type is not None:
        params["meetingType"] = meeting_type
    if state is not None:
        params["state"] = state
    if scheduled_type is not None:
        params["scheduledType"] = scheduled_type
    if is_modified is not None:
        params["isModified"] = is_modified
    if has_chat is not None:
        params["hasChat"] = has_chat
    if has_recording is not None:
        params["hasRecording"] = has_recording
    if has_transcription is not None:
        params["hasTranscription"] = has_transcription
    if has_summary is not None:
        params["hasSummary"] = has_summary
    if has_closed_caption is not None:
        params["hasClosedCaption"] = has_closed_caption
    if has_polls is not None:
        params["hasPolls"] = has_polls
    if has_qa is not None:
        params["hasQA"] = has_qa
    if has_slido is not None:
        params["hasSlido"] = has_slido
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if integration_tag is not None:
        params["integrationTag"] = integration_tag
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-meetings")
def create_meetings(
    scheduled_type: str = typer.Option(None, "--scheduled-type", help=""),
    allow_authenticated_devices: str = typer.Option(None, "--allow-authenticated-devices", help=""),
    agenda: str = typer.Option(None, "--agenda", help=""),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help=""),
    panelist_password: str = typer.Option(None, "--panelist-password", help=""),
    exclude_password: str = typer.Option(None, "--exclude-password", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    enable_connect_audio_before_host: str = typer.Option(None, "--enable-connect-audio-before-host", help=""),
    enabled_join_before_host: str = typer.Option(None, "--enabled-join-before-host", help=""),
    site_url: str = typer.Option(None, "--site-url", help=""),
    enabled_visual_watermark: str = typer.Option(None, "--enabled-visual-watermark", help=""),
    host_email: str = typer.Option(None, "--host-email", help=""),
    enabled_audio_watermark: str = typer.Option(None, "--enabled-audio-watermark", help=""),
    end: str = typer.Option(None, "--end", help=""),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help=""),
    enabled_breakout_sessions: str = typer.Option(None, "--enabled-breakout-sessions", help=""),
    title: str = typer.Option(None, "--title", help=""),
    allow_first_user_to_be_co_host: str = typer.Option(None, "--allow-first-user-to-be-co-host", help=""),
    password: str = typer.Option(None, "--password", help=""),
    adhoc: str = typer.Option(None, "--adhoc", help=""),
    start: str = typer.Option(None, "--start", help=""),
    send_email: str = typer.Option(None, "--send-email", help=""),
    require_attendee_login: str = typer.Option(None, "--require-attendee-login", help=""),
    restrict_to_invitees: str = typer.Option(None, "--restrict-to-invitees", help=""),
    enabled_live_stream: str = typer.Option(None, "--enabled-live-stream", help=""),
    recurrence: str = typer.Option(None, "--recurrence", help=""),
    room_id: str = typer.Option(None, "--room-id", help=""),
    enabled_auto_record_meeting: str = typer.Option(None, "--enabled-auto-record-meeting", help=""),
    allow_any_user_to_be_co_host: str = typer.Option(None, "--allow-any-user-to-be-co-host", help=""),
    template_id: str = typer.Option(None, "--template-id", help=""),
    public_meeting: str = typer.Option(None, "--public-meeting", help=""),
    reminder_time: str = typer.Option(None, "--reminder-time", help=""),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help=""),
    session_type_id: str = typer.Option(None, "--session-type-id", help=""),
    enabled_webcast_view: str = typer.Option(None, "--enabled-webcast-view", help=""),
    enable_automatic_lock: str = typer.Option(None, "--enable-automatic-lock", help=""),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Meeting\n\nExample --json-body:\n  '{"scheduledType":"...","allowAuthenticatedDevices":"...","meetingOptions":{"enabledFileTransfer":"...","enabledUCFRichMedia":"...","enabledChat":"...","enabledVideo":"...","enabledPolling":"...","enabledNote":"...","noteType":"..."},"trackingCodes":[{"name":"...","value":"..."}],"attendeePrivileges":{"enabledShareContent":"...","enabledSaveDocument":"...","enabledPrintDocument":"...","enabledAnnotate":"...","enabledViewParticipantList":"...","enabledViewThumbnails":"...","enabledRemoteControl":"...","enabledViewAnyDocument":"..."},"agenda":"...","joinBeforeHostMinutes":"...","panelistPassword":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if scheduled_type is not None:
            body["scheduledType"] = scheduled_type
        if allow_authenticated_devices is not None:
            body["allowAuthenticatedDevices"] = allow_authenticated_devices
        if agenda is not None:
            body["agenda"] = agenda
        if join_before_host_minutes is not None:
            body["joinBeforeHostMinutes"] = join_before_host_minutes
        if panelist_password is not None:
            body["panelistPassword"] = panelist_password
        if exclude_password is not None:
            body["excludePassword"] = exclude_password
        if timezone is not None:
            body["timezone"] = timezone
        if enable_connect_audio_before_host is not None:
            body["enableConnectAudioBeforeHost"] = enable_connect_audio_before_host
        if enabled_join_before_host is not None:
            body["enabledJoinBeforeHost"] = enabled_join_before_host
        if site_url is not None:
            body["siteUrl"] = site_url
        if enabled_visual_watermark is not None:
            body["enabledVisualWatermark"] = enabled_visual_watermark
        if host_email is not None:
            body["hostEmail"] = host_email
        if enabled_audio_watermark is not None:
            body["enabledAudioWatermark"] = enabled_audio_watermark
        if end is not None:
            body["end"] = end
        if visual_watermark_opacity is not None:
            body["visualWatermarkOpacity"] = visual_watermark_opacity
        if enabled_breakout_sessions is not None:
            body["enabledBreakoutSessions"] = enabled_breakout_sessions
        if title is not None:
            body["title"] = title
        if allow_first_user_to_be_co_host is not None:
            body["allowFirstUserToBeCoHost"] = allow_first_user_to_be_co_host
        if password is not None:
            body["password"] = password
        if adhoc is not None:
            body["adhoc"] = adhoc
        if start is not None:
            body["start"] = start
        if send_email is not None:
            body["sendEmail"] = send_email
        if require_attendee_login is not None:
            body["requireAttendeeLogin"] = require_attendee_login
        if restrict_to_invitees is not None:
            body["restrictToInvitees"] = restrict_to_invitees
        if enabled_live_stream is not None:
            body["enabledLiveStream"] = enabled_live_stream
        if recurrence is not None:
            body["recurrence"] = recurrence
        if room_id is not None:
            body["roomId"] = room_id
        if enabled_auto_record_meeting is not None:
            body["enabledAutoRecordMeeting"] = enabled_auto_record_meeting
        if allow_any_user_to_be_co_host is not None:
            body["allowAnyUserToBeCoHost"] = allow_any_user_to_be_co_host
        if template_id is not None:
            body["templateId"] = template_id
        if public_meeting is not None:
            body["publicMeeting"] = public_meeting
        if reminder_time is not None:
            body["reminderTime"] = reminder_time
        if unlocked_meeting_join_security is not None:
            body["unlockedMeetingJoinSecurity"] = unlocked_meeting_join_security
        if session_type_id is not None:
            body["sessionTypeId"] = session_type_id
        if enabled_webcast_view is not None:
            body["enabledWebcastView"] = enabled_webcast_view
        if enable_automatic_lock is not None:
            body["enableAutomaticLock"] = enable_automatic_lock
        if automatic_lock_minutes is not None:
            body["automaticLockMinutes"] = automatic_lock_minutes
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-bulk-insert")
def create_bulk_insert(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch register Meeting Registrants\n\nExample --json-body:\n  '{"items":[{"lastName":"...","address1":"...","address2":"...","city":"...","customizedQuestions":"...","zipCode":"...","state":"...","countryRegion":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/bulkInsert"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-end")
def create_end(
    meeting_id: str = typer.Argument(help="meetingId"),
    reason: str = typer.Option(None, "--reason", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """End a Meeting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/end"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if reason is not None:
            body["reason"] = reason
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("show-registrants")
def show_registrants(
    meeting_id: str = typer.Argument(help="meetingId"),
    registrant_id: str = typer.Argument(help="registrantId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Detailed Information for a Meeting Registrant."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/{registrant_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-registrants")
def create_registrants(
    meeting_id: str = typer.Argument(help="meetingId"),
    registrant_id: str = typer.Argument(help="registrantId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Update Meeting Registrants status\n\nExample --json-body:\n  '{"registrants":[{"id":"..."}],"sendEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/{registrant_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("delete-registrants")
def delete_registrants(
    meeting_id: str = typer.Argument(help="meetingId"),
    registrant_id: str = typer.Argument(help="registrantId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Registrant."""
    if not force:
        typer.confirm(f"Delete {registrant_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/{registrant_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {registrant_id}")



@app.command("create-reject")
def create_reject(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Reject Meeting Registrants\n\nExample --json-body:\n  '{"registrants":[{"id":"..."}],"sendEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/reject"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-cancel")
def create_cancel(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Cancel Meeting Registrants\n\nExample --json-body:\n  '{"registrants":[{"id":"..."}],"sendEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/cancel"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-query")
def create_query(
    meeting_id: str = typer.Argument(help="meetingId"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of registrants in the response, up"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    status: str = typer.Option(None, "--status", help=""),
    order_by: str = typer.Option(None, "--order-by", help=""),
    order_type: str = typer.Option(None, "--order-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Meeting Registrants\n\nExample --json-body:\n  '{"emails":["..."],"status":"...","orderBy":"...","orderType":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/query"
    params = {}
    if max is not None:
        params["max"] = max
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if status is not None:
            body["status"] = status
        if order_by is not None:
            body["orderBy"] = order_by
        if order_type is not None:
            body["orderType"] = order_type
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-bulk-delete")
def create_bulk_delete(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Delete Meeting Registrants\n\nExample --json-body:\n  '{"registrants":[{"id":"..."}],"sendEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/bulkDelete"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("list-meetings-admin")
def list_meetings_admin(
    meeting_number: str = typer.Option(None, "--meeting-number", help="Meeting number for the meeting objects being requested. `mee"),
    web_link: str = typer.Option(None, "--web-link", help="URL encoded link to information page for the meeting objects"),
    current: str = typer.Option(None, "--current", help="Flag identifying to retrieve the current scheduled meeting o"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meetings By an Admin."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetings"
    params = {}
    if meeting_number is not None:
        params["meetingNumber"] = meeting_number
    if web_link is not None:
        params["webLink"] = web_link
    if current is not None:
        params["current"] = current
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            if "max" not in params:
                params["max"] = 1000
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("list-interpreters")
def list_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Interpreters."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-interpreters")
def create_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    email: str = typer.Option(None, "--email", help=""),
    display_name: str = typer.Option(None, "--display-name", help=""),
    language_code1: str = typer.Option(None, "--language-code1", help=""),
    language_code2: str = typer.Option(None, "--language-code2", help=""),
    host_email: str = typer.Option(None, "--host-email", help=""),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Meeting Interpreter."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if email is not None:
            body["email"] = email
        if display_name is not None:
            body["displayName"] = display_name
        if language_code1 is not None:
            body["languageCode1"] = language_code1
        if language_code2 is not None:
            body["languageCode2"] = language_code2
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("list-breakout-sessions")
def list_breakout_sessions(
    meeting_id: str = typer.Argument(help="meetingId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Breakout Sessions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    params = {}
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("update-breakout-sessions")
def update_breakout_sessions(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help=""),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Breakout Sessions\n\nExample --json-body:\n  '{"hostEmail":"...","items":[{"name":"...","invitees":"..."}],"sendEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-breakout-sessions")
def delete_breakout_sessions(
    meeting_id: str = typer.Argument(help="meetingId"),
    send_email: str = typer.Option(None, "--send-email", help="Whether or not to send emails to host and invitees. It is an"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Meeting Breakout Sessions."""
    if not force:
        typer.confirm(f"Delete {meeting_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/breakoutSessions"
    params = {}
    if send_email is not None:
        params["sendEmail"] = send_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {meeting_id}")



@app.command("show-meetings")
def show_meetings(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("update-meetings")
def update_meetings(
    meeting_id: str = typer.Argument(help="meetingId"),
    allow_first_user_to_be_co_host: str = typer.Option(None, "--allow-first-user-to-be-co-host", help=""),
    allow_authenticated_devices: str = typer.Option(None, "--allow-authenticated-devices", help=""),
    agenda: str = typer.Option(None, "--agenda", help=""),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help=""),
    panelist_password: str = typer.Option(None, "--panelist-password", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    host_email: str = typer.Option(None, "--host-email", help=""),
    enabled_audio_watermark: str = typer.Option(None, "--enabled-audio-watermark", help=""),
    enabled_visual_watermark: str = typer.Option(None, "--enabled-visual-watermark", help=""),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help=""),
    title: str = typer.Option(None, "--title", help=""),
    start: str = typer.Option(None, "--start", help=""),
    password: str = typer.Option(None, "--password", help=""),
    send_email: str = typer.Option(None, "--send-email", help=""),
    end: str = typer.Option(None, "--end", help=""),
    enabled_breakout_sessions: str = typer.Option(None, "--enabled-breakout-sessions", help=""),
    require_attendee_login: str = typer.Option(None, "--require-attendee-login", help=""),
    restrict_to_invitees: str = typer.Option(None, "--restrict-to-invitees", help=""),
    enabled_live_stream: str = typer.Option(None, "--enabled-live-stream", help=""),
    recurrence: str = typer.Option(None, "--recurrence", help=""),
    enabled_join_before_host: str = typer.Option(None, "--enabled-join-before-host", help=""),
    enabled_auto_record_meeting: str = typer.Option(None, "--enabled-auto-record-meeting", help=""),
    allow_any_user_to_be_co_host: str = typer.Option(None, "--allow-any-user-to-be-co-host", help=""),
    enable_connect_audio_before_host: str = typer.Option(None, "--enable-connect-audio-before-host", help=""),
    exclude_password: str = typer.Option(None, "--exclude-password", help=""),
    public_meeting: str = typer.Option(None, "--public-meeting", help=""),
    reminder_time: str = typer.Option(None, "--reminder-time", help=""),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help=""),
    session_type_id: str = typer.Option(None, "--session-type-id", help=""),
    enabled_webcast_view: str = typer.Option(None, "--enabled-webcast-view", help=""),
    enable_automatic_lock: str = typer.Option(None, "--enable-automatic-lock", help=""),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Meeting\n\nExample --json-body:\n  '{"allowFirstUserToBeCoHost":"...","allowAuthenticatedDevices":"...","meetingOptions":{"enabledFileTransfer":"...","enabledUCFRichMedia":"...","enabledChat":"...","enabledVideo":"...","enabledPolling":"...","enabledNote":"...","noteType":"..."},"trackingCodes":[{"name":"...","value":"..."}],"attendeePrivileges":{"enabledShareContent":"...","enabledSaveDocument":"...","enabledPrintDocument":"...","enabledAnnotate":"...","enabledViewParticipantList":"...","enabledViewThumbnails":"...","enabledRemoteControl":"...","enabledViewAnyDocument":"..."},"agenda":"...","joinBeforeHostMinutes":"...","panelistPassword":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if allow_first_user_to_be_co_host is not None:
            body["allowFirstUserToBeCoHost"] = allow_first_user_to_be_co_host
        if allow_authenticated_devices is not None:
            body["allowAuthenticatedDevices"] = allow_authenticated_devices
        if agenda is not None:
            body["agenda"] = agenda
        if join_before_host_minutes is not None:
            body["joinBeforeHostMinutes"] = join_before_host_minutes
        if panelist_password is not None:
            body["panelistPassword"] = panelist_password
        if timezone is not None:
            body["timezone"] = timezone
        if host_email is not None:
            body["hostEmail"] = host_email
        if enabled_audio_watermark is not None:
            body["enabledAudioWatermark"] = enabled_audio_watermark
        if enabled_visual_watermark is not None:
            body["enabledVisualWatermark"] = enabled_visual_watermark
        if visual_watermark_opacity is not None:
            body["visualWatermarkOpacity"] = visual_watermark_opacity
        if title is not None:
            body["title"] = title
        if start is not None:
            body["start"] = start
        if password is not None:
            body["password"] = password
        if send_email is not None:
            body["sendEmail"] = send_email
        if end is not None:
            body["end"] = end
        if enabled_breakout_sessions is not None:
            body["enabledBreakoutSessions"] = enabled_breakout_sessions
        if require_attendee_login is not None:
            body["requireAttendeeLogin"] = require_attendee_login
        if restrict_to_invitees is not None:
            body["restrictToInvitees"] = restrict_to_invitees
        if enabled_live_stream is not None:
            body["enabledLiveStream"] = enabled_live_stream
        if recurrence is not None:
            body["recurrence"] = recurrence
        if enabled_join_before_host is not None:
            body["enabledJoinBeforeHost"] = enabled_join_before_host
        if enabled_auto_record_meeting is not None:
            body["enabledAutoRecordMeeting"] = enabled_auto_record_meeting
        if allow_any_user_to_be_co_host is not None:
            body["allowAnyUserToBeCoHost"] = allow_any_user_to_be_co_host
        if enable_connect_audio_before_host is not None:
            body["enableConnectAudioBeforeHost"] = enable_connect_audio_before_host
        if exclude_password is not None:
            body["excludePassword"] = exclude_password
        if public_meeting is not None:
            body["publicMeeting"] = public_meeting
        if reminder_time is not None:
            body["reminderTime"] = reminder_time
        if unlocked_meeting_join_security is not None:
            body["unlockedMeetingJoinSecurity"] = unlocked_meeting_join_security
        if session_type_id is not None:
            body["sessionTypeId"] = session_type_id
        if enabled_webcast_view is not None:
            body["enabledWebcastView"] = enabled_webcast_view
        if enable_automatic_lock is not None:
            body["enableAutomaticLock"] = enable_automatic_lock
        if automatic_lock_minutes is not None:
            body["automaticLockMinutes"] = automatic_lock_minutes
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("update-meetings-1")
def update_meetings_1(
    meeting_id: str = typer.Argument(help="meetingId"),
    allow_first_user_to_be_co_host: str = typer.Option(None, "--allow-first-user-to-be-co-host", help=""),
    allow_authenticated_devices: str = typer.Option(None, "--allow-authenticated-devices", help=""),
    agenda: str = typer.Option(None, "--agenda", help=""),
    join_before_host_minutes: str = typer.Option(None, "--join-before-host-minutes", help=""),
    panelist_password: str = typer.Option(None, "--panelist-password", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    host_email: str = typer.Option(None, "--host-email", help=""),
    enabled_audio_watermark: str = typer.Option(None, "--enabled-audio-watermark", help=""),
    enabled_visual_watermark: str = typer.Option(None, "--enabled-visual-watermark", help=""),
    visual_watermark_opacity: str = typer.Option(None, "--visual-watermark-opacity", help=""),
    title: str = typer.Option(None, "--title", help=""),
    start: str = typer.Option(None, "--start", help=""),
    password: str = typer.Option(None, "--password", help=""),
    send_email: str = typer.Option(None, "--send-email", help=""),
    end: str = typer.Option(None, "--end", help=""),
    enabled_breakout_sessions: str = typer.Option(None, "--enabled-breakout-sessions", help=""),
    require_attendee_login: str = typer.Option(None, "--require-attendee-login", help=""),
    restrict_to_invitees: str = typer.Option(None, "--restrict-to-invitees", help=""),
    enabled_live_stream: str = typer.Option(None, "--enabled-live-stream", help=""),
    recurrence: str = typer.Option(None, "--recurrence", help=""),
    enabled_join_before_host: str = typer.Option(None, "--enabled-join-before-host", help=""),
    enabled_auto_record_meeting: str = typer.Option(None, "--enabled-auto-record-meeting", help=""),
    allow_any_user_to_be_co_host: str = typer.Option(None, "--allow-any-user-to-be-co-host", help=""),
    enable_connect_audio_before_host: str = typer.Option(None, "--enable-connect-audio-before-host", help=""),
    exclude_password: str = typer.Option(None, "--exclude-password", help=""),
    public_meeting: str = typer.Option(None, "--public-meeting", help=""),
    reminder_time: str = typer.Option(None, "--reminder-time", help=""),
    unlocked_meeting_join_security: str = typer.Option(None, "--unlocked-meeting-join-security", help=""),
    session_type_id: str = typer.Option(None, "--session-type-id", help=""),
    enabled_webcast_view: str = typer.Option(None, "--enabled-webcast-view", help=""),
    enable_automatic_lock: str = typer.Option(None, "--enable-automatic-lock", help=""),
    automatic_lock_minutes: str = typer.Option(None, "--automatic-lock-minutes", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Patch a Meeting\n\nExample --json-body:\n  '{"allowFirstUserToBeCoHost":"...","allowAuthenticatedDevices":"...","meetingOptions":{"enabledFileTransfer":"...","enabledUCFRichMedia":"...","enabledChat":"...","enabledVideo":"...","enabledPolling":"...","enabledNote":"...","noteType":"..."},"trackingCodes":[{"name":"...","value":"..."}],"attendeePrivileges":{"enabledShareContent":"...","enabledSaveDocument":"...","enabledPrintDocument":"...","enabledAnnotate":"...","enabledViewParticipantList":"...","enabledViewThumbnails":"...","enabledRemoteControl":"...","enabledViewAnyDocument":"..."},"agenda":"...","joinBeforeHostMinutes":"...","panelistPassword":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if allow_first_user_to_be_co_host is not None:
            body["allowFirstUserToBeCoHost"] = allow_first_user_to_be_co_host
        if allow_authenticated_devices is not None:
            body["allowAuthenticatedDevices"] = allow_authenticated_devices
        if agenda is not None:
            body["agenda"] = agenda
        if join_before_host_minutes is not None:
            body["joinBeforeHostMinutes"] = join_before_host_minutes
        if panelist_password is not None:
            body["panelistPassword"] = panelist_password
        if timezone is not None:
            body["timezone"] = timezone
        if host_email is not None:
            body["hostEmail"] = host_email
        if enabled_audio_watermark is not None:
            body["enabledAudioWatermark"] = enabled_audio_watermark
        if enabled_visual_watermark is not None:
            body["enabledVisualWatermark"] = enabled_visual_watermark
        if visual_watermark_opacity is not None:
            body["visualWatermarkOpacity"] = visual_watermark_opacity
        if title is not None:
            body["title"] = title
        if start is not None:
            body["start"] = start
        if password is not None:
            body["password"] = password
        if send_email is not None:
            body["sendEmail"] = send_email
        if end is not None:
            body["end"] = end
        if enabled_breakout_sessions is not None:
            body["enabledBreakoutSessions"] = enabled_breakout_sessions
        if require_attendee_login is not None:
            body["requireAttendeeLogin"] = require_attendee_login
        if restrict_to_invitees is not None:
            body["restrictToInvitees"] = restrict_to_invitees
        if enabled_live_stream is not None:
            body["enabledLiveStream"] = enabled_live_stream
        if recurrence is not None:
            body["recurrence"] = recurrence
        if enabled_join_before_host is not None:
            body["enabledJoinBeforeHost"] = enabled_join_before_host
        if enabled_auto_record_meeting is not None:
            body["enabledAutoRecordMeeting"] = enabled_auto_record_meeting
        if allow_any_user_to_be_co_host is not None:
            body["allowAnyUserToBeCoHost"] = allow_any_user_to_be_co_host
        if enable_connect_audio_before_host is not None:
            body["enableConnectAudioBeforeHost"] = enable_connect_audio_before_host
        if exclude_password is not None:
            body["excludePassword"] = exclude_password
        if public_meeting is not None:
            body["publicMeeting"] = public_meeting
        if reminder_time is not None:
            body["reminderTime"] = reminder_time
        if unlocked_meeting_join_security is not None:
            body["unlockedMeetingJoinSecurity"] = unlocked_meeting_join_security
        if session_type_id is not None:
            body["sessionTypeId"] = session_type_id
        if enabled_webcast_view is not None:
            body["enabledWebcastView"] = enabled_webcast_view
        if enable_automatic_lock is not None:
            body["enableAutomaticLock"] = enable_automatic_lock
        if automatic_lock_minutes is not None:
            body["automaticLockMinutes"] = automatic_lock_minutes
    try:
        result = api.session.rest_patch(url, json=body)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-meetings")
def delete_meetings(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help="Whether or not to send emails to host and invitees. It is an"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting."""
    if not force:
        typer.confirm(f"Delete {meeting_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if send_email is not None:
        params["sendEmail"] = send_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {meeting_id}")



@app.command("list-survey")
def list_survey(
    meeting_id: str = typer.Argument(help="meetingId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Survey."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/survey"
    params = {}
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("questions", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("update-simultaneous-interpretation")
def update_simultaneous_interpretation(
    meeting_id: str = typer.Argument(help="meetingId"),
    enabled: str = typer.Option(None, "--enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Simultaneous interpretation\n\nExample --json-body:\n  '{"enabled":"...","interpreters":[{"languageCode2":"...","email":"...","displayName":"...","languageCode1":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/simultaneousInterpretation"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-meetings-admin")
def show_meetings_admin(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting By an Admin."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetings/{meeting_id}"
    params = {}
    if current is not None:
        params["current"] = current
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-approve")
def create_approve(
    meeting_id: str = typer.Argument(help="meetingId"),
    current: str = typer.Option(None, "--current", help="Whether or not to retrieve only the current scheduled meetin"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Batch Approve Meeting Registrants\n\nExample --json-body:\n  '{"registrants":[{"id":"..."}],"sendEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/registrants/approve"
    params = {}
    if current is not None:
        params["current"] = current
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if send_email is not None:
            body["sendEmail"] = send_email
    try:
        result = api.session.rest_post(url, json=body, params=params)
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("list-survey-results")
def list_survey_results(
    meeting_id: str = typer.Argument(help="meetingId"),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help="Start date and time (inclusive) in any [ISO 8601](https://en"),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help="End date and time (exclusive) in any [ISO 8601](https://en.w"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Survey Results."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/surveyResults"
    params = {}
    if meeting_start_time_from is not None:
        params["meetingStartTimeFrom"] = meeting_start_time_from
    if meeting_start_time_to is not None:
        params["meetingStartTimeTo"] = meeting_start_time_to
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("list-templates")
def list_templates(
    template_type: str = typer.Option(None, "--template-type", help="Meeting template type for the meeting template objects being"),
    locale: str = typer.Option(None, "--locale", help="Locale for the meeting template objects being requested. If"),
    is_default: str = typer.Option(None, "--is-default", help="The value is `true` or `false`. If it's `true`, return the d"),
    is_standard: str = typer.Option(None, "--is-standard", help="The value is `true` or `false`. If it's `true`, return the s"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists meeting templates"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Templates."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/templates"
    params = {}
    if template_type is not None:
        params["templateType"] = template_type
    if locale is not None:
        params["locale"] = locale
    if is_default is not None:
        params["isDefault"] = is_default
    if is_standard is not None:
        params["isStandard"] = is_standard
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-survey-links")
def create_survey_links(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help=""),
    meeting_start_time_from: str = typer.Option(None, "--meeting-start-time-from", help=""),
    meeting_start_time_to: str = typer.Option(None, "--meeting-start-time-to", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Survey Links\n\nExample --json-body:\n  '{"hostEmail":"...","emails":["..."],"meetingStartTimeFrom":"...","meetingStartTimeTo":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/surveyLinks"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if meeting_start_time_from is not None:
            body["meetingStartTimeFrom"] = meeting_start_time_from
        if meeting_start_time_to is not None:
            body["meetingStartTimeTo"] = meeting_start_time_to
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("create-join")
def create_join(
    email: str = typer.Option(None, "--email", help=""),
    display_name: str = typer.Option(None, "--display-name", help=""),
    create_join_link_as_web_link: str = typer.Option(None, "--create-join-link-as-web-link", help=""),
    host_email: str = typer.Option(None, "--host-email", help=""),
    web_link: str = typer.Option(None, "--web-link", help=""),
    meeting_id: str = typer.Option(None, "--meeting-id", help=""),
    meeting_number: str = typer.Option(None, "--meeting-number", help=""),
    create_start_link_as_web_link: str = typer.Option(None, "--create-start-link-as-web-link", help=""),
    password: str = typer.Option(None, "--password", help=""),
    registration_id: str = typer.Option(None, "--registration-id", help=""),
    join_directly: str = typer.Option(None, "--join-directly", help=""),
    expiration_minutes: str = typer.Option(None, "--expiration-minutes", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Join a Meeting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/join"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if email is not None:
            body["email"] = email
        if display_name is not None:
            body["displayName"] = display_name
        if create_join_link_as_web_link is not None:
            body["createJoinLinkAsWebLink"] = create_join_link_as_web_link
        if host_email is not None:
            body["hostEmail"] = host_email
        if web_link is not None:
            body["webLink"] = web_link
        if meeting_id is not None:
            body["meetingId"] = meeting_id
        if meeting_number is not None:
            body["meetingNumber"] = meeting_number
        if create_start_link_as_web_link is not None:
            body["createStartLinkAsWebLink"] = create_start_link_as_web_link
        if password is not None:
            body["password"] = password
        if registration_id is not None:
            body["registrationId"] = registration_id
        if join_directly is not None:
            body["joinDirectly"] = join_directly
        if expiration_minutes is not None:
            body["expirationMinutes"] = expiration_minutes
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("list-invitation-sources")
def list_invitation_sources(
    meeting_id: str = typer.Argument(help="meetingId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Invitation Sources."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/invitationSources"
    params = {}
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Start', 'start'), ('End', 'end'), ('State', 'state')], limit=limit)



@app.command("create-invitation-sources")
def create_invitation_sources(
    meeting_id: str = typer.Argument(help="meetingId"),
    host_email: str = typer.Option(None, "--host-email", help=""),
    person_id: str = typer.Option(None, "--person-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Invitation Sources\n\nExample --json-body:\n  '{"hostEmail":"...","items":[{"sourceId":"...","sourceEmail":"..."}],"personId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/invitationSources"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if person_id is not None:
            body["personId"] = person_id
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("show-interpreters")
def show_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    interpreter_id: str = typer.Argument(help="interpreterId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Meeting Interpreter."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
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



@app.command("update-interpreters")
def update_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    interpreter_id: str = typer.Argument(help="interpreterId"),
    email: str = typer.Option(None, "--email", help=""),
    display_name: str = typer.Option(None, "--display-name", help=""),
    language_code1: str = typer.Option(None, "--language-code1", help=""),
    language_code2: str = typer.Option(None, "--language-code2", help=""),
    host_email: str = typer.Option(None, "--host-email", help=""),
    send_email: str = typer.Option(None, "--send-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Meeting Interpreter."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if email is not None:
            body["email"] = email
        if display_name is not None:
            body["displayName"] = display_name
        if language_code1 is not None:
            body["languageCode1"] = language_code1
        if language_code2 is not None:
            body["languageCode2"] = language_code2
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-interpreters")
def delete_interpreters(
    meeting_id: str = typer.Argument(help="meetingId"),
    interpreter_id: str = typer.Argument(help="interpreterId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    send_email: str = typer.Option(None, "--send-email", help="If `true`, send email to the interpreter."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Interpreter."""
    if not force:
        typer.confirm(f"Delete {interpreter_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetings/{meeting_id}/interpreters/{interpreter_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if send_email is not None:
        params["sendEmail"] = send_email
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {interpreter_id}")


