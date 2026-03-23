import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling rooms.")


@app.command("list")
def cmd_list(
    team_id: str = typer.Option(None, "--team-id", help="List rooms associated with a team, by ID. Cannot be set in c"),
    type_param: str = typer.Option(None, "--type", help="Choices: direct, group"),
    org_public_spaces: str = typer.Option(None, "--org-public-spaces", help="Shows the org's public spaces joined and unjoined. When set"),
    from_param: str = typer.Option(None, "--from", help="Filters rooms, that were made public after this time. See `m"),
    to: str = typer.Option(None, "--to", help="Filters rooms, that were made public before this time. See `"),
    sort_by: str = typer.Option(None, "--sort-by", help="Choices: id, lastactivity, created"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of rooms in the response. Value mus"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    if max is not None:
        params["max"] = max
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
        print_table(items, columns=[('ID', 'id'), ('Title', 'title'), ('Type', 'type')], limit=limit)



@app.command("create")
def create(
    title: str = typer.Option(..., "--title", help="A user-friendly name for the room."),
    team_id: str = typer.Option(None, "--team-id", help="The ID for the team with which this room is associated."),
    classification_id: str = typer.Option(None, "--classification-id", help="The `classificationId` for the room."),
    is_locked: bool = typer.Option(None, "--is-locked/--no-is-locked", help="Set the space as locked/moderated and the creator becomes a"),
    is_public: bool = typer.Option(None, "--is-public/--no-is-public", help="The room is public and therefore discoverable within the org"),
    description: str = typer.Option(None, "--description", help="The description of the space."),
    is_announcement_only: bool = typer.Option(None, "--is-announcement-only/--no-is-announcement-only", help="Sets the space into announcement Mode."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Room."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms"
    if json_body:
        body = json.loads(json_body)
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



@app.command("show")
def show(
    room_id: str = typer.Argument(help="roomId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Room Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms/{room_id}"
    try:
        result = api.session.rest_get(url)
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



@app.command("update")
def update(
    room_id: str = typer.Argument(help="roomId"),
    title: str = typer.Option(None, "--title", help="A user-friendly name for the room."),
    classification_id: str = typer.Option(None, "--classification-id", help="The classificationId for the room."),
    team_id: str = typer.Option(None, "--team-id", help="The teamId to which this space should be assigned. Only unow"),
    is_locked: bool = typer.Option(None, "--is-locked/--no-is-locked", help="Set the space as locked/moderated and the creator becomes a"),
    is_public: bool = typer.Option(None, "--is-public/--no-is-public", help="The room is public and therefore discoverable within the org"),
    description: str = typer.Option(None, "--description", help="The description of the space."),
    is_announcement_only: bool = typer.Option(None, "--is-announcement-only/--no-is-announcement-only", help="Sets the space into Announcement Mode or clears the Anouncem"),
    is_read_only: bool = typer.Option(None, "--is-read-only/--no-is-read-only", help="A compliance officer can set a direct room as read-only, whi"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Room."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms/{room_id}"
    if json_body:
        body = json.loads(json_body)
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
    room_id: str = typer.Argument(help="roomId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Room."""
    if not force:
        typer.confirm(f"Delete {room_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms/{room_id}"
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
    typer.echo(f"Deleted: {room_id}")



@app.command("show-meeting-info")
def show_meeting_info(
    room_id: str = typer.Argument(help="roomId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Room Meeting Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/rooms/{room_id}/meetingInfo"
    try:
        result = api.session.rest_get(url)
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


