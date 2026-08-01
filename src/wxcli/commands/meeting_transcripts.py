import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Meetings meeting-transcripts.")


@app.command("list", short_help="List Meeting Transcripts.")
def cmd_list(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for transcripts to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List transcripts to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`."),
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the [meeting instance](/docs/meetings#meeting-series-scheduled-meetings-and-meeting-instances) to which the transcript belongs. Please note that currently the meeting ID of a scheduled [personal..."),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the `admin-level` scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user. If `meetingId`..."),
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site from which the API lists transcripts. If not specified, the API lists transcripts from user's preferred site. All available Webex sites and the preferred site of the user can be retrieved by the [Get Site List](/docs/api/v1/meeting-preferences/get-site-list) API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Transcripts."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingTranscripts"
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
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Meeting Topic', 'meetingTopic'), ('Meeting ID', 'meetingId'), ('Start Time', 'startTime'), ('Status', 'status')], limit=limit)



@app.command("list-meeting-transcripts", short_help="List Meeting Transcripts For Compliance Officer.")
def list_meeting_transcripts(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for transcripts to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List transcripts to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`."),
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site from which the API lists transcripts."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Meeting Transcripts For Compliance Officer.\n\n\b\nExample: wxcli meeting-transcripts list-meeting-transcripts --site-url SITE_URL"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meetingTranscripts"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if site_url is not None:
        params["siteUrl"] = site_url
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Meeting Topic', 'meetingTopic'), ('Meeting ID', 'meetingId'), ('Start Time', 'startTime'), ('Status', 'status')], limit=limit)



@app.command("list-download", short_help="Download a Meeting Transcript.")
def list_download(
    transcript_id: str = typer.Argument(help="from: wxcli meeting-transcripts list"),
    format_param: str = typer.Option(None, "--format", help="Choices: vtt, txt"),
    host_email: str = typer.Option(None, "--host-email", help="Email address for the meeting host. This parameter is only used if the user or application calling the API has the `admin-level` scopes. If set, the admin may specify the email of a user in a site they manage and the API will return details for a meeting that is hosted by that user."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Download a Meeting Transcript.\n\n\b\nExample: wxcli meeting-transcripts list-download TRANSCRIPT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingTranscripts/{transcript_id}/download"
    params = {}
    if format_param is not None:
        params["format"] = format_param
    if host_email is not None:
        params["hostEmail"] = host_email
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
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-snippets", short_help="List Snippets of a Meeting Transcript.")
def list_snippets(
    transcript_id: str = typer.Argument(help="from: wxcli meeting-transcripts list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Snippets of a Meeting Transcript.\n\n\b\nExample: wxcli meeting-transcripts list-snippets TRANSCRIPT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingTranscripts/{transcript_id}/snippets"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Person Name', 'personName'), ('Text', 'text')], limit=limit)



@app.command("show", short_help="Get a Transcript Snippet.")
def show(
    transcript_id: str = typer.Argument(help="from: wxcli meeting-transcripts list"),
    snippet_id: str = typer.Argument(help="from: wxcli meeting-transcripts list-snippets"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Transcript Snippet.\n\n\b\nExample: wxcli meeting-transcripts show TRANSCRIPT_ID SNIPPET_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingTranscripts/{transcript_id}/snippets/{snippet_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"text":"...","reason":"..."}'

@app.command("update", short_help="Update a Transcript Snippet.")
def update(
    transcript_id: str = typer.Argument(help="from: wxcli meeting-transcripts list"),
    snippet_id: str = typer.Argument(help="from: wxcli meeting-transcripts list-snippets"),
    reason: str = typer.Option(None, "--reason", help="Reason for snippet update; only required for Compliance Officers."),
    text: str = typer.Option(None, "--text", help="Text for the snippet."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Transcript Snippet.\n\n\b\nExample: wxcli meeting-transcripts update TRANSCRIPT_ID SNIPPET_ID --text TEXT\n\n\b\nExample --json-body: '{"text":"...","reason":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meetingTranscripts/{transcript_id}/snippets/{snippet_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if reason is not None:
            body["reason"] = reason
        if text is not None:
            body["text"] = text
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": snippet_id}, output=output, fields=fields)



_BODY_SKELETON_DELETE = '{"reason":"...","comment":"..."}'

@app.command("delete", short_help="Delete a Transcript.")
def delete(
    transcript_id: str = typer.Argument(help="from: wxcli meeting-transcripts list"),
    reason: str = typer.Option(None, "--reason", help="Reason for deleting a transcript. Only required when a Compliance Officer is operating on another user's transcript."),
    comment: str = typer.Option(None, "--comment", help="Explanation for deleting a transcript. The comment can be a maximum of 255 characters long."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Transcript.\n\n\b\nExample: wxcli meeting-transcripts delete TRANSCRIPT_ID\n\n\b\nExample --json-body: '{"reason":"...","comment":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {transcript_id}?", abort=True)
    url = f"https://webexapis.com/v1/meetingTranscripts/{transcript_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if reason is not None:
            body["reason"] = reason
        if comment is not None:
            body["comment"] = comment
    try:
        result = api.session.rest_delete(url, json=body or None)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {transcript_id}")
    else:
        emit({"status": "deleted", "id": transcript_id}, output=output, fields=fields)


