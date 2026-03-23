import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling recordings.")


@app.command("list")
def cmd_list(
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `ma"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to retu"),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the parent meeting series, scheduled m"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API lists recordings. I"),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key of the parent meeting created by an integration"),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings"),
    format_param: str = typer.Option(None, "--format", help="Choices: MP4, ARF"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: MeetingCenter, EventCenter, SupportCenter, TrainingCenter"),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted, purged"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Recordings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings"
    params = {}
    if max is not None:
        params["max"] = max
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if host_email is not None:
        params["hostEmail"] = host_email
    if site_url is not None:
        params["siteUrl"] = site_url
    if integration_tag is not None:
        params["integrationTag"] = integration_tag
    if topic is not None:
        params["topic"] = topic
    if format_param is not None:
        params["format"] = format_param
    if service_type is not None:
        params["serviceType"] = service_type
    if status is not None:
        params["status"] = status
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
        print_table(items, columns=[('ID', 'id'), ('Topic', 'topic'), ('Format', 'format'), ('Created', 'timeRecorded')], limit=limit)



@app.command("list-recordings-admin")
def list_recordings_admin(
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `ma"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to retu"),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the parent meeting series, scheduled m"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists recordings from. I"),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key of the parent meeting created by an integration"),
    topic: str = typer.Option(None, "--topic", help="Recording topic. If specified, the API filters recordings by"),
    format_param: str = typer.Option(None, "--format", help="Choices: MP4, ARF"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: MeetingCenter, EventCenter, SupportCenter, TrainingCenter"),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted, purged"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Recordings For an Admin or Compliance Officer."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/recordings"
    params = {}
    if max is not None:
        params["max"] = max
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if site_url is not None:
        params["siteUrl"] = site_url
    if integration_tag is not None:
        params["integrationTag"] = integration_tag
    if topic is not None:
        params["topic"] = topic
    if format_param is not None:
        params["format"] = format_param
    if service_type is not None:
        params["serviceType"] = service_type
    if status is not None:
        params["status"] = status
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
        print_table(items, columns=[('ID', 'id'), ('Topic', 'topic'), ('Format', 'format'), ('Created', 'timeRecorded')], limit=limit)



@app.command("delete")
def delete(
    recording_id: str = typer.Argument(help="recordingId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Recording By an Admin."""
    if not force:
        typer.confirm(f"Delete {recording_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/recordings/{recording_id}"
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {recording_id}")



@app.command("show")
def show(
    recording_id: str = typer.Argument(help="recordingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. Only used if the user or"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Recording Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/{recording_id}"
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



@app.command("delete-recordings")
def delete_recordings(
    recording_id: str = typer.Argument(help="recordingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. Only used if the user or"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Recording."""
    if not force:
        typer.confirm(f"Delete {recording_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/{recording_id}"
    params = {}
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {recording_id}")



@app.command("create")
def create(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. Only used if the user or"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API deletes recordings."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Move Recordings into the Recycle Bin\n\nExample --json-body:\n  '{"recordingIds":["..."],"siteUrl":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/softDelete"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-restore")
def create_restore(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only u"),
    restore_all: bool = typer.Option(None, "--restore-all/--no-restore-all", help="If not specified or `false`, restores the recordings specifi"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API restores recordings"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Restore Recordings from Recycle Bin\n\nExample --json-body:\n  '{"restoreAll":true,"recordingIds":["..."],"siteUrl":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/restore"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if restore_all is not None:
            body["restoreAll"] = restore_all
        if site_url is not None:
            body["siteUrl"] = site_url
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-purge")
def create_purge(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. Only used if the user or"),
    purge_all: bool = typer.Option(None, "--purge-all/--no-purge-all", help="If not specified or `false`, purges the recordings specified"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API purges recordings."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge Recordings from Recycle Bin\n\nExample --json-body:\n  '{"purgeAll":true,"recordingIds":["..."],"siteUrl":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/purge"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if purge_all is not None:
            body["purgeAll"] = purge_all
        if site_url is not None:
            body["siteUrl"] = site_url
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-access-list-recordings")
def create_access_list_recordings(
    recording_id: str = typer.Argument(help="recordingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether to send email notifications to the users being share"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Share a Recording\n\nExample --json-body:\n  '{"hostEmail":"...","addEmails":["..."],"removeEmails":["..."],"sendEmail":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/{recording_id}/accessList"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-access-list-recordings-1")
def create_access_list_recordings_1(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should on"),
    web_share_link: str = typer.Option(None, "--web-share-link", help="The link for the recording to be shared or unshared."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether to send email notifications to the users being share"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Share a Recording Link\n\nExample --json-body:\n  '{"hostEmail":"...","webShareLink":"...","addEmails":["..."],"removeEmails":["..."],"sendEmail":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/accessList"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if web_share_link is not None:
            body["webShareLink"] = web_share_link
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-recordings-group")
def list_recordings_group(
    person_id: str = typer.Option(None, "--person-id", help="Person ID of the user whose recordings will be retrieved. Th"),
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `ma"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to retu"),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists recordings from. I"),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key of the parent meeting created by an integration"),
    topic: str = typer.Option(None, "--topic", help="Recording topic. If specified, the API filters recordings by"),
    format_param: str = typer.Option(None, "--format", help="Choices: MP4, ARF"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: MeetingCenter, EventCenter, SupportCenter, TrainingCenter"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Group Recordings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/group/recordings"
    params = {}
    if person_id is not None:
        params["personId"] = person_id
    if max is not None:
        params["max"] = max
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if site_url is not None:
        params["siteUrl"] = site_url
    if integration_tag is not None:
        params["integrationTag"] = integration_tag
    if topic is not None:
        params["topic"] = topic
    if format_param is not None:
        params["format"] = format_param
    if service_type is not None:
        params["serviceType"] = service_type
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
        print_table(items, columns=[('ID', 'id'), ('Topic', 'topic'), ('Format', 'format'), ('Created', 'timeRecorded')], limit=limit)



@app.command("show-recordings")
def show_recordings(
    recording_id: str = typer.Argument(help="recordingId"),
    person_id: str = typer.Option(None, "--person-id", help="Person ID of the user whose recordings will be retrieved. Th"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Group Recording Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/group/recordings/{recording_id}"
    params = {}
    if person_id is not None:
        params["personId"] = person_id
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


