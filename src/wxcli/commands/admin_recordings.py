import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling admin-recordings.")


@app.command("list")
def cmd_list(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`."),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the parent meeting series, scheduled meeting, or meeting instance for which recordings are being requested. If a meeting series ID is specified, the operation returns an array of recordings for the specified meeting series. If a scheduled meeting ID is specified, the operation..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the required [admin-level meeting scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API lists recordings. If not specified, the API lists recordings from all of a user's sites. All available Webex sites and the preferred site of the user can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key of the parent meeting created by an integration application. This parameter is used by the integration application to query recordings by a key in its own domain, such as a Zendesk ticket ID, a Jira ID, a Salesforce Opportunity ID, etc. An integrationTag created by one client cannot be..."),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings by topic in a case-insensitive manner."),
    format_param: str = typer.Option(None, "--format", help="Choices: MP4, ARF"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: MeetingCenter, EventCenter, SupportCenter, TrainingCenter"),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted, purged"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Recordings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings"
    params = {}
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
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Topic', 'topic'), ('Format', 'format'), ('Created', 'timeRecorded')], limit=limit)



_BODY_SKELETON_CREATE = '{"max":0,"from":"...","to":"...","meetingId":"...","siteUrl":"...","integrationTag":"...","hostEmail":"...","topic":"..."}'

@app.command("create")
def create(
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `max` must be equal to or greater than `1` and equal to or less than `100`."),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for query recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`."),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the parent meeting series, scheduled meeting, or meeting instance for which recordings are being requested. If a meeting series ID is specified, the operation returns an array of recordings for the specified meeting series. If a scheduled meeting ID is specified, the operation..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API lists recordings. If not specified, the API lists recordings from all of a user's sites. All available Webex sites and the preferred site of the user can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key of the parent meeting created by an integration application. This parameter is used by the integration application to query recordings by a key in its own domain, such as a Zendesk ticket ID, a Jira ID, a Salesforce Opportunity ID, etc. An integrationTag created by one client cannot be..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This property is only used if the caller has admin-level meeting scopes. If set, the admin may specify the email of a user in a site they manage and the API will return recordings of that user."),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings by topic in a case-insensitive manner."),
    format_param: str = typer.Option(None, "--format", help="Choices: MP4, ARF"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: MeetingCenter, EventCenter, SupportCenter, TrainingCenter"),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted, purged"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Recordings\n\nExample --json-body:\n  '{"max":0,"from":"...","to":"...","meetingId":"...","siteUrl":"...","integrationTag":"...","hostEmail":"...","topic":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/query"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if max is not None:
            body["max"] = max
        if from_param is not None:
            body["from"] = from_param
        if to is not None:
            body["to"] = to
        if meeting_id is not None:
            body["meetingId"] = meeting_id
        if site_url is not None:
            body["siteUrl"] = site_url
        if integration_tag is not None:
            body["integrationTag"] = integration_tag
        if host_email is not None:
            body["hostEmail"] = host_email
        if topic is not None:
            body["topic"] = topic
        if format_param is not None:
            body["format"] = format_param
        if service_type is not None:
            body["serviceType"] = service_type
        if status is not None:
            body["status"] = status
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



@app.command("list-recordings-admin")
def list_recordings_admin(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. The interval between `from` and `to` must be within 30 days. If `to` is specified, the default value for `from` is `to` minus 7 days...."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. The interval between `from` and `to` must be within 30 days. If `from` is specified, the default value for `to` is `from` plus 7..."),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the parent meeting series, scheduled meeting, or meeting instance for which recordings are being requested. If a meeting series ID is specified, the operation returns an array of recordings for the specified meeting series. If a scheduled meeting ID is specified, the operation..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists recordings from. If not specified, the API lists recordings from user's preferred site. All available Webex sites and preferred site of the user can be retrieved by [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key of the parent meeting created by an integration application. This parameter is used by the integration application to query recordings by a key in its own domain such as a Zendesk ticket ID, a Jira ID, a Salesforce Opportunity ID, etc. An integrationTag created by one client cannot be..."),
    topic: str = typer.Option(None, "--topic", help="Recording topic. If specified, the API filters recordings by topic in a case-insensitive manner."),
    format_param: str = typer.Option(None, "--format", help="Choices: MP4, ARF"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: MeetingCenter, EventCenter, SupportCenter, TrainingCenter"),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted, purged"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Recordings For an Admin or Compliance Officer."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/recordings"
    params = {}
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
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Topic', 'topic'), ('Format', 'format'), ('Created', 'timeRecorded')], limit=limit)



_BODY_SKELETON_CREATE_QUERY = '{"max":0,"from":"...","to":"...","meetingId":"...","siteUrl":"...","integrationTag":"...","topic":"...","format":"MP4"}'

@app.command("create-query")
def create_query(
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `max` must be equal to or greater than `1` and equal to or less than `100`."),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for query recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`."),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the parent meeting series, scheduled meeting, or meeting instance for which recordings are being requested. If a meeting series ID is specified, the operation returns an array of recordings for the specified meeting series. If a scheduled meeting ID is specified, the operation..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists recordings from. If not specified, the API lists recordings from user's preferred site. All available Webex sites and preferred site of the user can be retrieved by [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key of the parent meeting created by an integration application. This parameter is used by the integration application to query recordings by a key in its own domain such as a Zendesk ticket ID, a Jira ID, a Salesforce Opportunity ID, etc. An integrationTag created by one client cannot be..."),
    topic: str = typer.Option(None, "--topic", help="Recording topic. If specified, the API filters recordings by topic in a case-insensitive manner."),
    format_param: str = typer.Option(None, "--format", help="Choices: MP4, ARF"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: MeetingCenter, EventCenter, SupportCenter, TrainingCenter"),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted, purged"),
    timezone: str = typer.Option(None, "--timezone", help="Optional timezone override for the request (if not provided, UTC is used)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Recordings For an Admin or Compliance Officer\n\nExample --json-body:\n  '{"max":0,"from":"...","to":"...","meetingId":"...","siteUrl":"...","integrationTag":"...","topic":"...","format":"MP4"}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_QUERY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/recordings/query"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if max is not None:
            body["max"] = max
        if from_param is not None:
            body["from"] = from_param
        if to is not None:
            body["to"] = to
        if meeting_id is not None:
            body["meetingId"] = meeting_id
        if site_url is not None:
            body["siteUrl"] = site_url
        if integration_tag is not None:
            body["integrationTag"] = integration_tag
        if topic is not None:
            body["topic"] = topic
        if format_param is not None:
            body["format"] = format_param
        if service_type is not None:
            body["serviceType"] = service_type
        if status is not None:
            body["status"] = status
        if timezone is not None:
            body["timezone"] = timezone
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



@app.command("delete")
def delete(
    recording_id: str = typer.Argument(help="recordingId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Recording By an Admin."""
    if not force:
        typer.confirm(f"Delete {recording_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/recordings/{recording_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {recording_id}")
    else:
        emit({"status": "deleted", "id": recording_id}, output=output, fields=fields)



@app.command("show")
def show(
    recording_id: str = typer.Argument(help="recordingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. Only used if the user or application calling the API has required [admin-level meeting scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage, and the API will return..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_DELETE_RECORDINGS = '{"reason":"...","comment":"..."}'

@app.command("delete-recordings")
def delete_recordings(
    recording_id: str = typer.Argument(help="recordingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. Only used if the user or application calling the API has the required [admin-level meeting scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will delete a..."),
    reason: str = typer.Option(None, "--reason", help="Reason for deleting a recording. Only required when a Compliance Officer is operating on another user's recording."),
    comment: str = typer.Option(None, "--comment", help="Compliance Officer's explanation for deleting a recording. The comment can be a maximum of 255 characters long."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Recording\n\nExample --json-body:\n  '{"reason":"...","comment":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE_RECORDINGS), indent=2))
        raise typer.Exit(0)
    if not force:
        typer.confirm(f"Delete {recording_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/{recording_id}"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if reason is not None:
            body["reason"] = reason
        if comment is not None:
            body["comment"] = comment
    try:
        result = api.session.rest_delete(url, json=body or None, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {recording_id}")
    else:
        emit({"status": "deleted", "id": recording_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_SOFT_DELETE = '{"recordingIds":["..."],"siteUrl":"..."}'

@app.command("create-soft-delete")
def create_soft_delete(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. Only used if the user or application calling the API has the required [admin-level meeting scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will move..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API deletes recordings. If not specified, the API deletes recordings from the user's preferred site. All available Webex sites and preferred sites of a user can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Move Recordings into the Recycle Bin\n\nExample --json-body:\n  '{"recordingIds":["..."],"siteUrl":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SOFT_DELETE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/softDelete"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
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



_BODY_SKELETON_CREATE_RESTORE = '{"restoreAll":true,"recordingIds":["..."],"siteUrl":"..."}'

@app.command("create-restore")
def create_restore(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the required [admin-level meeting scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the..."),
    restore_all: bool = typer.Option(None, "--restore-all/--no-restore-all", help="If not specified or `false`, restores the recordings specified by `recordingIds`. If `true`, restores all recordings from the recycle bin."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API restores recordings. If not specified, the API restores recordings from a user's preferred site. All available Webex sites and preferred sites of a user can be retrieved by [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Restore Recordings from Recycle Bin\n\nExample --json-body:\n  '{"restoreAll":true,"recordingIds":["..."],"siteUrl":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_RESTORE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/restore"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if restore_all is not None:
            body["restoreAll"] = restore_all
        if site_url is not None:
            body["siteUrl"] = site_url
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



_BODY_SKELETON_CREATE_PURGE = '{"purgeAll":true,"recordingIds":["..."],"siteUrl":"..."}'

@app.command("create-purge")
def create_purge(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. Only used if the user or application calling the API has the required [admin-level meeting scopes](/docs/meetings#adminorganization-level-authentication-and-scopes). If set, the admin may specify the email of a user in a site they manage and the API will purge..."),
    purge_all: bool = typer.Option(None, "--purge-all/--no-purge-all", help="If not specified or `false`, purges the recordings specified by `recordingIds`. If `true`, purges all recordings from the recycle bin."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API purges recordings. If not specified, the API purges recordings from user's preferred site. All available Webex sites and preferred sites of the user can be retrieved by [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge Recordings from Recycle Bin\n\nExample --json-body:\n  '{"purgeAll":true,"recordingIds":["..."],"siteUrl":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_PURGE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/purge"
    params = {}
    if host_email is not None:
        params["hostEmail"] = host_email
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if purge_all is not None:
            body["purgeAll"] = purge_all
        if site_url is not None:
            body["siteUrl"] = site_url
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        typer.echo("Purged.")
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_ACCESS_LIST_RECORDINGS = '{"hostEmail":"...","addEmails":["..."],"removeEmails":["..."],"sendEmail":true}'

@app.command("create-access-list-recordings")
def create_access_list_recordings(
    recording_id: str = typer.Argument(help="recordingId"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin-level scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host. The field is not editable and is only used to share or..."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether to send email notifications to the users being shared. The default is `true`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Share a Recording\n\nExample --json-body:\n  '{"hostEmail":"...","addEmails":["..."],"removeEmails":["..."],"sendEmail":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ACCESS_LIST_RECORDINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/{recording_id}/accessList"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if host_email is not None:
            body["hostEmail"] = host_email
        if send_email is not None:
            body["sendEmail"] = send_email
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



_BODY_SKELETON_CREATE_ACCESS_LIST_RECORDINGS_1 = '{"hostEmail":"...","webShareLink":"...","addEmails":["..."],"removeEmails":["..."],"sendEmail":true}'

@app.command("create-access-list-recordings-1")
def create_access_list_recordings_1(
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This attribute should only be set if the user or application calling the API has the admin-level scopes. When used, the admin may specify the email of a user in a site they manage to be the meeting host. The field is not editable and is only used to share or..."),
    web_share_link: str = typer.Option(None, "--web-share-link", help="The link for the recording to be shared or unshared."),
    send_email: bool = typer.Option(None, "--send-email/--no-send-email", help="Whether to send email notifications to the users being shared. The default is `true`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Share a Recording Link\n\nExample --json-body:\n  '{"hostEmail":"...","webShareLink":"...","addEmails":["..."],"removeEmails":["..."],"sendEmail":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ACCESS_LIST_RECORDINGS_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/recordings/accessList"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("list-recordings-group")
def list_recordings_group(
    person_id: str = typer.Option(None, "--person-id", help="Person ID of the user whose recordings will be retrieved. The person ID can be retrieved from the [People APIs](/docs/api/v1/people), e.g. [Lit People](/docs/api/v1/people/list-people). Note that a person ID retrieved from the People APIs is a Base64-encoded string, e.g...."),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. The interval between `from` and `to` must be within 30 days."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. The interval between `from` and `to` must be within 30 days."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API lists recordings from. If not specified, the API lists recordings from user's preferred site. All available Webex sites and preferred site of the user can be retrieved by [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    integration_tag: str = typer.Option(None, "--integration-tag", help="External key of the parent meeting created by an integration application. This parameter is used by the integration application to query recordings by a key in its own domain such as a Zendesk ticket ID, a Jira ID, a Salesforce Opportunity ID, etc. An integrationTag created by one client cannot be..."),
    format_param: str = typer.Option(None, "--format", help="Choices: MP4, ARF"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: MeetingCenter, EventCenter, SupportCenter, TrainingCenter"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Group Recordings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/group/recordings"
    params = {}
    if person_id is not None:
        params["personId"] = person_id
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if site_url is not None:
        params["siteUrl"] = site_url
    if integration_tag is not None:
        params["integrationTag"] = integration_tag
    if format_param is not None:
        params["format"] = format_param
    if service_type is not None:
        params["serviceType"] = service_type
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Topic', 'topic'), ('Format', 'format'), ('Created', 'timeRecorded')], limit=limit)



@app.command("show-recordings")
def show_recordings(
    recording_id: str = typer.Argument(help="recordingId"),
    person_id: str = typer.Option(None, "--person-id", help="Person ID of the user whose recordings will be retrieved. The person ID can be retrieved from the [People APIs](/docs/api/v1/people), e.g. [Lit People](/docs/api/v1/people/list-people). Note that a person ID retrieved from the People APIs is a Base64-encoded string, e.g...."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


