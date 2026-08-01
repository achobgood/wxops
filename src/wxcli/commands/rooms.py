import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling rooms.")


@app.command("list", short_help="List Rooms.")
def cmd_list(
    team_id: str = typer.Option(None, "--team-id", help="List rooms associated with a team, by ID. Cannot be set in combination with `orgPublicSpaces`."),
    type_param: str = typer.Option(None, "--type", help="Choices: direct, group"),
    org_public_spaces: str = typer.Option(None, "--org-public-spaces", help="Shows the org's public spaces joined and unjoined. When set the result list is sorted by the `madePublic` timestamp."),
    from_param: str = typer.Option(None, "--from", help="Filters rooms, that were made public after this time. See `madePublic` timestamp"),
    to: str = typer.Option(None, "--to", help="Filters rooms, that were made public before this time. See `maePublic` timestamp"),
    sort_by: str = typer.Option(None, "--sort-by", help="Choices: id, lastactivity, created"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Rooms."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms"
    params = {}
    if team_id is not None:
        params["teamId"] = team_id
    if type_param is not None:
        params["type"] = type_param
    if org_public_spaces is not None:
        params["orgPublicSpaces"] = org_public_spaces
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if sort_by is not None:
        params["sortBy"] = sort_by
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Title', 'title'), ('Type', 'type')], limit=limit)



_BODY_SKELETON_CREATE = '{"title":"...","teamId":"...","classificationId":"...","isLocked":true,"isPublic":true,"description":"...","isAnnouncementOnly":true}'

@app.command("create", short_help="Create a Room.")
def create(
    title: str = typer.Option(None, "--title", help="(required) A user-friendly name for the room."),
    team_id: str = typer.Option(None, "--team-id", help="The ID for the team with which this room is associated."),
    classification_id: str = typer.Option(None, "--classification-id", help="The `classificationId` for the room."),
    is_locked: bool = typer.Option(None, "--is-locked/--no-is-locked", help="Set the space as locked/moderated and the creator becomes a moderator"),
    is_public: bool = typer.Option(None, "--is-public/--no-is-public", help="The room is public and therefore discoverable within the org. Anyone can find and join that room. When `true` the `description` must be filled in."),
    description: str = typer.Option(None, "--description", help="The description of the space."),
    is_announcement_only: bool = typer.Option(None, "--is-announcement-only/--no-is-announcement-only", help="Sets the space into announcement Mode."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Room.\n\n\b\nExample: wxcli rooms create --title TITLE\n\n\b\nExample --json-body: '{"title":"...","teamId":"...","classificationId":"...","isLocked":true,"isPublic":true,"description":"...","isAnnouncementOnly":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if title is not None:
            body["title"] = title
        if team_id is not None:
            body["teamId"] = team_id
        if classification_id is not None:
            body["classificationId"] = classification_id
        if is_locked is not None:
            body["isLocked"] = is_locked
        if is_public is not None:
            body["isPublic"] = is_public
        if description is not None:
            body["description"] = description
        if is_announcement_only is not None:
            body["isAnnouncementOnly"] = is_announcement_only
        _missing = [f for f in ['title'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Room Details.")
def show(
    room_id: str = typer.Argument(help="Webex ROOM id, from: wxcli rooms list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Room Details.\n\n\b\nExample: wxcli rooms show ROOM_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms/{room_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"title":"...","classificationId":"...","teamId":"...","isLocked":true,"isPublic":true,"description":"...","isAnnouncementOnly":true,"isReadOnly":true}'

@app.command("update", short_help="Update a Room.")
def update(
    room_id: str = typer.Argument(help="Webex ROOM id, from: wxcli rooms list"),
    title: str = typer.Option(None, "--title", help="A user-friendly name for the room."),
    classification_id: str = typer.Option(None, "--classification-id", help="The classificationId for the room."),
    team_id: str = typer.Option(None, "--team-id", help="The teamId to which this space should be assigned. Only unowned spaces can be assigned to a team. Assignment between teams is unsupported."),
    is_locked: bool = typer.Option(None, "--is-locked/--no-is-locked", help="Set the space as locked/moderated and the creator becomes a moderator"),
    is_public: bool = typer.Option(None, "--is-public/--no-is-public", help="The room is public and therefore discoverable within the org. Anyone can find and join that room. When `true` the `description` must be filled in."),
    description: str = typer.Option(None, "--description", help="The description of the space."),
    is_announcement_only: bool = typer.Option(None, "--is-announcement-only/--no-is-announcement-only", help="Sets the space into Announcement Mode or clears the Anouncement Mode (`false`)"),
    is_read_only: bool = typer.Option(None, "--is-read-only/--no-is-read-only", help="A compliance officer can set a direct room as read-only, which will disallow any new information exchanges in this space, while maintaing historical data."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Room.\n\n\b\nExample: wxcli rooms update ROOM_ID --title TITLE\n\n\b\nExample --json-body: '{"title":"...","classificationId":"...","teamId":"...","isLocked":true,"isPublic":true,"description":"...","isAnnouncementOnly":true,"isReadOnly":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms/{room_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if title is not None:
            body["title"] = title
        if classification_id is not None:
            body["classificationId"] = classification_id
        if team_id is not None:
            body["teamId"] = team_id
        if is_locked is not None:
            body["isLocked"] = is_locked
        if is_public is not None:
            body["isPublic"] = is_public
        if description is not None:
            body["description"] = description
        if is_announcement_only is not None:
            body["isAnnouncementOnly"] = is_announcement_only
        if is_read_only is not None:
            body["isReadOnly"] = is_read_only
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
        emit({"status": "updated", "id": room_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Room.")
def delete(
    room_id: str = typer.Argument(help="Webex ROOM id, from: wxcli rooms list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Room.\n\n\b\nExample: wxcli rooms delete ROOM_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {room_id}?", abort=True)
    url = f"https://webexapis.com/v1/rooms/{room_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {room_id}")
    else:
        emit({"status": "deleted", "id": room_id}, output=output, fields=fields)



@app.command("show-meeting-info", short_help="Get Room Meeting Details.")
def show_meeting_info(
    room_id: str = typer.Argument(help="Webex ROOM id, from: wxcli rooms list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Room Meeting Details.\n\n\b\nExample: wxcli rooms show-meeting-info ROOM_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms/{room_id}/meetingInfo"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


