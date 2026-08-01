import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling memberships.")


@app.command("list", short_help="List Memberships.")
def cmd_list(
    room_id: str = typer.Option(None, "--room-id", help="List memberships associated with a room, by ID."),
    person_id: str = typer.Option(None, "--person-id", help="List memberships associated with a person, by ID. The `roomId` parameter is required when using this parameter."),
    person_email: str = typer.Option(None, "--person-email", help="List memberships associated with a person, by email address. The `roomId` parameter is required when using this parameter."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Memberships."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/memberships"
    params = {}
    if room_id is not None:
        params["roomId"] = room_id
    if person_id is not None:
        params["personId"] = person_id
    if person_email is not None:
        params["personEmail"] = person_email
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Person', 'personDisplayName'), ('Email', 'personEmail'), ('Moderator', 'isModerator')], limit=limit)



_BODY_SKELETON_CREATE = '{"roomId":"...","personId":"...","personEmail":"...","isModerator":true}'

@app.command("create", short_help="Create a Membership.")
def create(
    room_id: str = typer.Option(None, "--room-id", help="(required) The room ID."),
    person_id: str = typer.Option(None, "--person-id", help="The person ID."),
    person_email: str = typer.Option(None, "--person-email", help="The email address of the person."),
    is_moderator: bool = typer.Option(None, "--is-moderator/--no-is-moderator", help="Whether or not the participant is a room moderator."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Membership.\n\n\b\nExample: wxcli memberships create --room-id ROOM_ID\n\n\b\nExample --json-body: '{"roomId":"...","personId":"...","personEmail":"...","isModerator":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/memberships"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if room_id is not None:
            body["roomId"] = room_id
        if person_id is not None:
            body["personId"] = person_id
        if person_email is not None:
            body["personEmail"] = person_email
        if is_moderator is not None:
            body["isModerator"] = is_moderator
        _missing = [f for f in ['roomId'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Membership Details.")
def show(
    membership_id: str = typer.Argument(help="Webex MEMBERSHIP id, from: wxcli memberships list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Membership Details.\n\n\b\nExample: wxcli memberships show MEMBERSHIP_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/memberships/{membership_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"isModerator":true,"isRoomHidden":true}'

@app.command("update", short_help="Update a Membership.")
def update(
    membership_id: str = typer.Argument(help="Webex MEMBERSHIP id, from: wxcli memberships list"),
    is_moderator: bool = typer.Option(None, "--is-moderator/--no-is-moderator", help="Whether or not the participant is a room moderator."),
    is_room_hidden: bool = typer.Option(None, "--is-room-hidden/--no-is-room-hidden", help="When set to true, hides direct spaces in the teams client. Any new message will make the room visible again."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Membership.\n\n\b\nExample: wxcli memberships update MEMBERSHIP_ID --is-moderator --is-room-hidden\n\n\b\nExample --json-body: '{"isModerator":true,"isRoomHidden":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/memberships/{membership_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if is_moderator is not None:
            body["isModerator"] = is_moderator
        if is_room_hidden is not None:
            body["isRoomHidden"] = is_room_hidden
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
        emit({"status": "updated", "id": membership_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Membership.")
def delete(
    membership_id: str = typer.Argument(help="Webex MEMBERSHIP id, from: wxcli memberships list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Membership.\n\n\b\nExample: wxcli memberships delete MEMBERSHIP_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {membership_id}?", abort=True)
    url = f"https://webexapis.com/v1/memberships/{membership_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {membership_id}")
    else:
        emit({"status": "deleted", "id": membership_id}, output=output, fields=fields)


