import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling people.")


@app.command("list")
def cmd_list(
    email: str = typer.Option(None, "--email", help="List people with this email address. For non-admin requests,"),
    display_name: str = typer.Option(None, "--display-name", help="List people whose name starts with this string. For non-admi"),
    id_param: str = typer.Option(None, "--id", help="List people by ID. Accepts up to 85 person IDs separated by"),
    roles: str = typer.Option(None, "--roles", help="List of roleIds separated by commas."),
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    location_id: str = typer.Option(None, "--location-id", help="List people present in this location."),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of people in the response. If `call"),
    exclude_status: str = typer.Option(None, "--exclude-status", help="Omit people status/availability to enhance query performance"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    if max is not None:
        params["max"] = max
    if exclude_status is not None:
        params["excludeStatus"] = exclude_status
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Email', 'emails[0]')], limit=limit)



@app.command("create")
def create(
    extension: str = typer.Option(None, "--extension", help=""),
    location_id: str = typer.Option(None, "--location-id", help=""),
    display_name: str = typer.Option(None, "--display-name", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    avatar: str = typer.Option(None, "--avatar", help=""),
    org_id: str = typer.Option(None, "--org-id", help=""),
    department: str = typer.Option(None, "--department", help=""),
    manager: str = typer.Option(None, "--manager", help=""),
    manager_id: str = typer.Option(None, "--manager-id", help=""),
    title: str = typer.Option(None, "--title", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people"
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
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show")
def show(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update")
def update(
    person_id: str = typer.Argument(help="personId"),
    display_name: str = typer.Option(None, "--display-name", help=""),
    extension: str = typer.Option(None, "--extension", help=""),
    location_id: str = typer.Option(None, "--location-id", help=""),
    first_name: str = typer.Option(None, "--first-name", help=""),
    last_name: str = typer.Option(None, "--last-name", help=""),
    nick_name: str = typer.Option(None, "--nick-name", help=""),
    avatar: str = typer.Option(None, "--avatar", help=""),
    org_id: str = typer.Option(None, "--org-id", help=""),
    department: str = typer.Option(None, "--department", help=""),
    manager: str = typer.Option(None, "--manager", help=""),
    manager_id: str = typer.Option(None, "--manager-id", help=""),
    title: str = typer.Option(None, "--title", help=""),
    login_enabled: bool = typer.Option(None, "--login-enabled/--no-login-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if display_name is not None:
            body["displayName"] = display_name
        if extension is not None:
            body["extension"] = extension
        if location_id is not None:
            body["locationId"] = location_id
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
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
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {person_id}")



@app.command("list-me")
def list_me(
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get My Own Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/me"
    params = {}
    if calling_data is not None:
        params["callingData"] = calling_data
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("me", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


