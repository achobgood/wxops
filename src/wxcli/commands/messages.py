import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling messages.")


@app.command("list")
def cmd_list(
    room_id: str = typer.Option(..., "--room-id", help="List messages in a room, by ID."),
    parent_id: str = typer.Option(None, "--parent-id", help="List messages with a parent, by ID."),
    mentioned_people: str = typer.Option(None, "--mentioned-people", help="List messages with these people mentioned, by ID. Use `me` a"),
    before: str = typer.Option(None, "--before", help="List messages sent before a date and time."),
    before_message: str = typer.Option(None, "--before-message", help="List messages sent before a message, by ID."),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of messages in the response. Cannot"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Messages."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/messages"
    params = {}
    if room_id is not None:
        params["roomId"] = room_id
    if parent_id is not None:
        params["parentId"] = parent_id
    if mentioned_people is not None:
        params["mentionedPeople"] = mentioned_people
    if before is not None:
        params["before"] = before
    if before_message is not None:
        params["beforeMessage"] = before_message
    if max is not None:
        params["max"] = max
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Person Email', 'personEmail'), ('Text', 'text')], limit=limit)



@app.command("create")
def create(
    room_id: str = typer.Option(None, "--room-id", help="The room ID of the message."),
    parent_id: str = typer.Option(None, "--parent-id", help="The parent message to reply to."),
    to_person_id: str = typer.Option(None, "--to-person-id", help="The person ID of the recipient when sending a private 1:1 me"),
    to_person_email: str = typer.Option(None, "--to-person-email", help="The email address of the recipient when sending a private 1:"),
    text: str = typer.Option(None, "--text", help="The message, in plain text. If `markdown` is specified this"),
    markdown: str = typer.Option(None, "--markdown", help="The message, in Markdown format. The maximum message length"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Message\n\nExample --json-body:\n  '{"roomId":"...","parentId":"...","toPersonId":"...","toPersonEmail":"...","text":"...","markdown":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/messages"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if room_id is not None:
            body["roomId"] = room_id
        if parent_id is not None:
            body["parentId"] = parent_id
        if to_person_id is not None:
            body["toPersonId"] = to_person_id
        if to_person_email is not None:
            body["toPersonEmail"] = to_person_email
        if text is not None:
            body["text"] = text
        if markdown is not None:
            body["markdown"] = markdown
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



@app.command("list-direct")
def list_direct(
    parent_id: str = typer.Option(None, "--parent-id", help="List messages with a parent, by ID."),
    person_id: str = typer.Option(None, "--person-id", help="List messages in a 1:1 room, by person ID."),
    person_email: str = typer.Option(None, "--person-email", help="List messages in a 1:1 room, by person email."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Direct Messages."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/messages/direct"
    params = {}
    if parent_id is not None:
        params["parentId"] = parent_id
    if person_id is not None:
        params["personId"] = person_id
    if person_email is not None:
        params["personEmail"] = person_email
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
        print_table(items, columns=[('ID', 'id'), ('Person Email', 'personEmail'), ('Text', 'text')], limit=limit)



@app.command("show")
def show(
    message_id: str = typer.Argument(help="messageId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Message Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/messages/{message_id}"
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
    message_id: str = typer.Argument(help="messageId"),
    room_id: str = typer.Option(None, "--room-id", help="The room ID of the message."),
    text: str = typer.Option(None, "--text", help="The message, in plain text. If `markdown` is specified this"),
    markdown: str = typer.Option(None, "--markdown", help="The message, in Markdown format. If this attribute is set en"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Edit a Message."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/messages/{message_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if room_id is not None:
            body["roomId"] = room_id
        if text is not None:
            body["text"] = text
        if markdown is not None:
            body["markdown"] = markdown
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
    message_id: str = typer.Argument(help="messageId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Message."""
    if not force:
        typer.confirm(f"Delete {message_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/messages/{message_id}"
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
    typer.echo(f"Deleted: {message_id}")


