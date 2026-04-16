import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling people.")


@app.command("list")
def cmd_list(
    email: str = typer.Option(None, "--email", help="List people with this email address. For non-admin requests,"),
    display_name: str = typer.Option(None, "--display-name", help="List people whose name starts with this string. For non-admi"),
    id_param: str = typer.Option(None, "--id", help="List people by ID. Accepts up to 85 person IDs separated by"),
    roles: str = typer.Option(None, "--roles", help="List of roleIds separated by commas."),
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    location_id: str = typer.Option(None, "--location-id", help="List people present in this location."),
    exclude_status: str = typer.Option(None, "--exclude-status", help="Omit people status/availability to enhance query performance"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List People."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people"
    params = {}
    if email is not None:
        params["email"] = email
    if display_name is not None:
        params["displayName"] = display_name
    if id_param is not None:
        params["id"] = id_param
    if roles is not None:
        params["roles"] = roles
    if calling_data is not None:
        params["callingData"] = calling_data
    if location_id is not None:
        params["locationId"] = location_id
    if exclude_status is not None:
        params["excludeStatus"] = exclude_status
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Email', 'emails[0]')], limit=limit)



@app.command("create")
def create(
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    min_response: str = typer.Option(None, "--min-response", help="Set to `true` to improve performance by omitting person deta"),
    extension: str = typer.Option(None, "--extension", help="Webex Calling extension of the person. This is only settable"),
    location_id: str = typer.Option(None, "--location-id", help="The ID of the location for this person."),
    display_name: str = typer.Option(None, "--display-name", help="The full name of the person."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the person."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the person."),
    avatar: str = typer.Option(None, "--avatar", help="The URL to the person's avatar in PNG format."),
    org_id: str = typer.Option(None, "--org-id", help="The ID of the organization to which this person belongs."),
    department: str = typer.Option(None, "--department", help="The business department the user belongs to."),
    manager: str = typer.Option(None, "--manager", help="A manager identifier."),
    manager_id: str = typer.Option(None, "--manager-id", help="Person ID of the manager."),
    title: str = typer.Option(None, "--title", help="The person's title."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Person\n\nExample --json-body:\n  '{"emails":["..."],"phoneNumbers":[{"type":"...","value":"..."}],"extension":"...","locationId":"...","displayName":"...","firstName":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people"
    params = {}
    if calling_data is not None:
        params["callingData"] = calling_data
    if min_response is not None:
        params["minResponse"] = min_response
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if extension is not None:
            body["extension"] = extension
        if location_id is not None:
            body["locationId"] = location_id
        if display_name is not None:
            body["displayName"] = display_name
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if avatar is not None:
            body["avatar"] = avatar
        if org_id is not None:
            body["orgId"] = org_id
        if department is not None:
            body["department"] = department
        if manager is not None:
            body["manager"] = manager
        if manager_id is not None:
            body["managerId"] = manager_id
        if title is not None:
            body["title"] = title
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



@app.command("show")
def show(
    person_id: str = typer.Argument(help="personId"),
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}"
    params = {}
    if calling_data is not None:
        params["callingData"] = calling_data
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
    person_id: str = typer.Argument(help="personId"),
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    show_all_types: str = typer.Option(None, "--show-all-types", help="Include additional user data like `#attendee` role."),
    min_response: str = typer.Option(None, "--min-response", help="Set to `true` to improve performance by omitting person deta"),
    extension: str = typer.Option(None, "--extension", help="Webex Calling extension of the person. This is only settable"),
    location_id: str = typer.Option(None, "--location-id", help="The ID of the location for this person."),
    display_name: str = typer.Option(None, "--display-name", help="The full name of the person."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the person."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the person."),
    nick_name: str = typer.Option(None, "--nick-name", help="The nickname of the person if configured. This cannot be ove"),
    avatar: str = typer.Option(None, "--avatar", help="The URL to the person's avatar in PNG format."),
    org_id: str = typer.Option(None, "--org-id", help="The ID of the organization to which this person belongs."),
    department: str = typer.Option(None, "--department", help="The business department the user belongs to."),
    manager: str = typer.Option(None, "--manager", help="A manager identifier."),
    manager_id: str = typer.Option(None, "--manager-id", help="Person ID of the manager."),
    title: str = typer.Option(None, "--title", help="The person's title."),
    login_enabled: bool = typer.Option(None, "--login-enabled/--no-login-enabled", help="Whether or not the user is allowed to use Webex. This proper"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Person\n\nExample --json-body:\n  '{"emails":["..."],"phoneNumbers":[{"type":"...","value":"..."}],"extension":"...","locationId":"...","displayName":"...","firstName":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}"
    params = {}
    if calling_data is not None:
        params["callingData"] = calling_data
    if show_all_types is not None:
        params["showAllTypes"] = show_all_types
    if min_response is not None:
        params["minResponse"] = min_response
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if extension is not None:
            body["extension"] = extension
        if location_id is not None:
            body["locationId"] = location_id
        if display_name is not None:
            body["displayName"] = display_name
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if nick_name is not None:
            body["nickName"] = nick_name
        if avatar is not None:
            body["avatar"] = avatar
        if org_id is not None:
            body["orgId"] = org_id
        if department is not None:
            body["department"] = department
        if manager is not None:
            body["manager"] = manager
        if manager_id is not None:
            body["managerId"] = manager_id
        if title is not None:
            body["title"] = title
        if login_enabled is not None:
            body["loginEnabled"] = login_enabled
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



@app.command("delete")
def delete(
    person_id: str = typer.Argument(help="personId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Person."""
    if not force:
        typer.confirm(f"Delete {person_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}"
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
    typer.echo(f"Deleted: {person_id}")



@app.command("show-me")
def show_me(
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Own Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/me"
    params = {}
    if calling_data is not None:
        params["callingData"] = calling_data
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


