import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling user-call-settings-members-me.")


@app.command("show", hidden=True)
@app.command("show-summary", short_help="Get Message Summary.")
def show_summary(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, virtual line, auto attendant, hunt group, or call queue for which there is a secondary line on a device owned by the authenticated user, or that was shared with the authenticated user."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Message Summary."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/members/me/summary"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list", hidden=True)
@app.command("list-voice-messages", short_help="List Messages. (Calling)")
def list_voice_messages(
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, virtual line, auto attendant, hunt group, or call queue for which there is a secondary line on a device owned by the authenticated user, or that was shared with the authenticated user."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Messages."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/members/me/voiceMessages"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Duration', 'duration'), ('Urgent', 'urgent'), ('Confidential', 'confidential'), ('Read', 'read')], limit=limit)



@app.command("delete", hidden=True)
@app.command("delete-voice-messages", short_help="Delete Message.")
def delete_voice_messages(
    message_id: str = typer.Argument(help="from: wxcli user-call-settings-members-me list-voice-messages"),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, virtual line, auto attendant, hunt group, or call queue for which there is a secondary line on a device owned by the authenticated user, or that was shared with the authenticated user."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Message.\n\n\b\nExample: wxcli user-call-settings-members-me delete-voice-messages MESSAGE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {message_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/members/me/voiceMessages/{message_id}"
    params = {}
    if line_owner_id is not None:
        params["lineOwnerId"] = line_owner_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {message_id}")
    else:
        emit({"status": "deleted", "id": message_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_MARK_AS_READ = '{"messageId":"...","lineOwnerId":"..."}'

@app.command("create", hidden=True)
@app.command("create-mark-as-read", short_help="Mark As Read.")
def create_mark_as_read(
    message_id: str = typer.Option(None, "--message-id", help="The voicemail message identifier of the message to mark as read. If the `messageId` is not provided, then all voicemail messages for the user are marked as read."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, virtual line, auto attendant, hunt group, or call queue for which there is a secondary line on a device owned by the authenticated user, or that was shared with the authenticated user."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mark As Read.\n\n\b\nExample --json-body: '{"messageId":"...","lineOwnerId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_MARK_AS_READ), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/members/me/markAsRead"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if message_id is not None:
            body["messageId"] = message_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



_BODY_SKELETON_CREATE_MARK_AS_UNREAD = '{"messageId":"...","lineOwnerId":"..."}'

@app.command("create-mark-as-unread", short_help="Mark As Unread.")
def create_mark_as_unread(
    message_id: str = typer.Option(None, "--message-id", help="The voicemail message identifier of the message to mark as unread. If the `messageId` is not provided, then all voicemail messages for the user are marked as unread."),
    line_owner_id: str = typer.Option(None, "--line-owner-id", help="The ID of a user, workspace, virtual line, auto attendant, hunt group, or call queue for which there is a secondary line on a device owned by the authenticated user, or that was shared with the authenticated user."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Mark As Unread.\n\n\b\nExample --json-body: '{"messageId":"...","lineOwnerId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_MARK_AS_UNREAD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/members/me/markAsUnread"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if message_id is not None:
            body["messageId"] = message_id
        if line_owner_id is not None:
            body["lineOwnerId"] = line_owner_id
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



@app.command("list-memberships", short_help="List Voice Message Memberships.")
def list_memberships(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Voice Message Memberships."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/voiceMessages/members/me/memberships"
    params = {}
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
    items = result.get("memberOf", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Type', 'type'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)


