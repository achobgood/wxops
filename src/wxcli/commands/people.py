import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling people.")


@app.command("list", short_help="List People.")
def cmd_list(
    email: str = typer.Option(None, "--email", help="List people with this email address. For non-admin requests, either this or `displayName` are required. With the exception of partner admins and a managed org relationship, people lookup by email is only available for users in the same org."),
    display_name: str = typer.Option(None, "--display-name", help="List people whose name starts with this string. For non-admin requests, either this or email are required."),
    id_param: str = typer.Option(None, "--id", help="List people by ID. Accepts up to 85 person IDs separated by commas. If this parameter is provided then presence information (such as the `lastActivity` or `status` properties) will not be included in the response."),
    roles: str = typer.Option(None, "--roles", help="List of roleIds separated by commas."),
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    location_id: str = typer.Option(None, "--location-id", help="List people present in this location."),
    exclude_status: str = typer.Option(None, "--exclude-status", help="Omit people status/availability to enhance query performance."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Email', 'emails')], limit=limit, params=params, expansions=('callingData',))



_BODY_SKELETON_CREATE = '{"emails":["..."],"phoneNumbers":[{"type":"work","value":"..."}],"extension":"...","locationId":"...","displayName":"...","firstName":"...","lastName":"...","avatar":"...","orgId":"...","roles":["..."],"licenses":["..."],"department":"...","manager":"...","managerId":"...","title":"...","addresses":[{"type":"...","country":"...","locality":"...","region":"...","streetAddress":"...","postalCode":"..."}],"siteUrls":["..."]}'

@app.command("create", short_help="Create a Person. (Calling)")
def create(
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    min_response: str = typer.Option(None, "--min-response", help="Set to `true` to improve performance by omitting person details and returning only the ID in the response when successful. If unsuccessful the response will have optional error details."),
    extension: str = typer.Option(None, "--extension", help="Webex Calling extension of the person. This is only settable for a person with a Webex Calling license."),
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
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Person.\n\n\b\nExample: wxcli people create --json-body '{"emails":["..."]}'\n\n\b\nExample --json-body: '{"emails":["..."],"phoneNumbers":[{"type":"work","value":"..."}],"extension":"...","locationId":"...","displayName":"...","firstName":"...","lastName":"...","avatar":"...","orgId":"...","roles":["..."],"licenses":["..."],"department":"...","manager":"...","managerId":"...","title":"...","addresses":[{"type":"...","country":"...","locality":"...","region":"...","streetAddress":"...","postalCode":"..."}],"siteUrls":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people"
    params = {}
    if calling_data is not None:
        params["callingData"] = calling_data
    if min_response is not None:
        params["minResponse"] = min_response
    if json_body:
        body = load_json_body(json_body)
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
        emit(result, output=output, fields=fields, params=params, expansions=('callingData',))



@app.command("show", short_help="Get Person Details.")
def show(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Person Details.\n\n\b\nExample: wxcli people show PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}"
    params = {}
    if calling_data is not None:
        params["callingData"] = calling_data
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields, params=params, expansions=('callingData',))



_BODY_SKELETON_UPDATE = '{"displayName":"...","emails":["..."],"phoneNumbers":[{"type":"work","value":"..."}],"extension":"...","locationId":"...","firstName":"...","lastName":"...","nickName":"...","avatar":"...","orgId":"...","roles":["..."],"licenses":["..."],"department":"...","manager":"...","managerId":"...","title":"...","addresses":[{"type":"...","country":"...","locality":"...","region":"...","streetAddress":"...","postalCode":"..."}],"siteUrls":["..."],"loginEnabled":true}'

@app.command("update", short_help="Update a Person.")
def update(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    show_all_types: str = typer.Option(None, "--show-all-types", help="Include additional user data like `#attendee` role."),
    min_response: str = typer.Option(None, "--min-response", help="Set to `true` to improve performance by omitting person details in the response. If unsuccessful the response will have optional error details."),
    extension: str = typer.Option(None, "--extension", help="Webex Calling extension of the person. This is only settable for a person with a Webex Calling license."),
    location_id: str = typer.Option(None, "--location-id", help="The ID of the location for this person."),
    display_name: str = typer.Option(None, "--display-name", help="The full name of the person."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the person."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the person."),
    nick_name: str = typer.Option(None, "--nick-name", help="The nickname of the person if configured. This cannot be overwritten and instead will be set to the firstName automatically in update requests."),
    avatar: str = typer.Option(None, "--avatar", help="The URL to the person's avatar in PNG format."),
    org_id: str = typer.Option(None, "--org-id", help="The ID of the organization to which this person belongs."),
    department: str = typer.Option(None, "--department", help="The business department the user belongs to."),
    manager: str = typer.Option(None, "--manager", help="A manager identifier."),
    manager_id: str = typer.Option(None, "--manager-id", help="Person ID of the manager."),
    title: str = typer.Option(None, "--title", help="The person's title."),
    login_enabled: bool = typer.Option(None, "--login-enabled/--no-login-enabled", help="Whether or not the user is allowed to use Webex. This property is only accessible if the authenticated user is an admin user for the person's organization."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Person.\n\n\b\nExample: wxcli people update PERSON_ID --display-name DISPLAY_NAME\n\n\b\nExample --json-body: '{"displayName":"...","emails":["..."],"phoneNumbers":[{"type":"work","value":"..."}],"extension":"...","locationId":"...","firstName":"...","lastName":"...","nickName":"...","avatar":"...","orgId":"...","roles":["..."],"licenses":["..."],"department":"...","manager":"...","managerId":"...","title":"...","addresses":[{"type":"...","country":"...","locality":"...","region":"...","streetAddress":"...","postalCode":"..."}],"siteUrls":["..."],"loginEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
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
        body = load_json_body(json_body)
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields, params=params, expansions=('callingData',))
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Person.")
def delete(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Person.\n\n\b\nExample: wxcli people delete PERSON_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {person_id}?", abort=True)
    url = f"https://webexapis.com/v1/people/{person_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {person_id}")
    else:
        emit({"status": "deleted", "id": person_id}, output=output, fields=fields)



@app.command("show-me", short_help="Get My Own Details.")
def show_me(
    calling_data: str = typer.Option(None, "--calling-data", help="Include Webex Calling user details in the response."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields, params=params, expansions=('callingData',))


