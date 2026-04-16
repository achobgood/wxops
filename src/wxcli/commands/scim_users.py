import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling scim-users.")


@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="The URL encoded filter. If the value is empty, the API will"),
    attributes: str = typer.Option(None, "--attributes", help="A multi-valued list of string names for resource attributes"),
    excluded_attributes: str = typer.Option(None, "--excluded-attributes", help="A multi-valued list of strings names for resource attributes"),
    sort_by: str = typer.Option(None, "--sort-by", help="A string for the attribute whose value can be used to order"),
    sort_order: str = typer.Option(None, "--sort-order", help="A string for the order in which the 'sortBy' parameter is ap"),
    start_index: str = typer.Option(None, "--start-index", help="An integer for the 1-based index of the first query result."),
    count: str = typer.Option(None, "--count", help="An integer for the maximum number of query results per page."),
    return_groups: str = typer.Option(None, "--return-groups", help="Define whether the group information needs to be returned."),
    include_group_details: str = typer.Option(None, "--include-group-details", help="Define whether the group information with details needs to b"),
    group_usage_types: str = typer.Option(None, "--group-usage-types", help="Returns groups with details of the specified group type."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search users."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Users"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if excluded_attributes is not None:
        params["excludedAttributes"] = excluded_attributes
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_order is not None:
        params["sortOrder"] = sort_order
    if start_index is not None:
        params["startIndex"] = start_index
    if count is not None:
        params["count"] = count
    if return_groups is not None:
        params["returnGroups"] = return_groups
    if include_group_details is not None:
        params["includeGroupDetails"] = include_group_details
    if group_usage_types is not None:
        params["groupUsageTypes"] = group_usage_types
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("Resources", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('User Name', 'userName'), ('Active', 'active')], limit=limit)



@app.command("create")
def create(
    user_name: str = typer.Option(None, "--user-name", help="(required) A unique identifier for the user that authenticates the user"),
    user_type: str = typer.Option(None, "--user-type", help="(required) Choices: user, room, external_calling, calling_service"),
    title: str = typer.Option(None, "--title", help="The user's business title.  Examples of a title is \"Business"),
    active: bool = typer.Option(None, "--active/--no-active", help="A boolean value of \"true\" or \"false\" indicating whether the"),
    preferred_language: str = typer.Option(None, "--preferred-language", help="User's preferred language. Acceptable values are based on th"),
    locale: str = typer.Option(None, "--locale", help="The user's locale which represents the user's currency, time"),
    timezone: str = typer.Option(None, "--timezone", help="The user's time zone specified in the [IANA timezone](https:"),
    profile_url: str = typer.Option(None, "--profile-url", help="A fully qualified URL pointing to a page representing the us"),
    external_id: str = typer.Option(None, "--external-id", help="User identifier provided by an external provisioning source."),
    display_name: str = typer.Option(None, "--display-name", help="The name displayed for the user in Webex."),
    nick_name: str = typer.Option(None, "--nick-name", help="A casual name of the user. For example, Bob when the user's"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a user\n\nExample --json-body:\n  '{"schemas":["..."],"userName":"...","userType":"user","title":"...","active":true,"roles":[{"value":"...","type":"...","display":"..."}]}'."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Users"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if user_name is not None:
            body["userName"] = user_name
        if user_type is not None:
            body["userType"] = user_type
        if title is not None:
            body["title"] = title
        if active is not None:
            body["active"] = active
        if preferred_language is not None:
            body["preferredLanguage"] = preferred_language
        if locale is not None:
            body["locale"] = locale
        if timezone is not None:
            body["timezone"] = timezone
        if profile_url is not None:
            body["profileUrl"] = profile_url
        if external_id is not None:
            body["externalId"] = external_id
        if display_name is not None:
            body["displayName"] = display_name
        if nick_name is not None:
            body["nickName"] = nick_name
        _missing = [f for f in ['userName', 'userType'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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
    user_id: str = typer.Argument(help="userId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a user."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Users/{user_id}"
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
    user_id: str = typer.Argument(help="userId"),
    user_name: str = typer.Option(None, "--user-name", help="A unique identifier for the user and authenticates the user"),
    user_type: str = typer.Option(None, "--user-type", help="Choices: user, room, external_calling, calling_service"),
    title: str = typer.Option(None, "--title", help="The user's business title.  Examples of a title is \"Business"),
    active: bool = typer.Option(None, "--active/--no-active", help="A boolean value of \"true\" or \"false\" indicating whether the"),
    preferred_language: str = typer.Option(None, "--preferred-language", help="User's preferred language.  Acceptable values for this field"),
    locale: str = typer.Option(None, "--locale", help="The user's locale which represents the user's currency, time"),
    timezone: str = typer.Option(None, "--timezone", help="The user's time zone specified in the [IANA timezone](https:"),
    profile_url: str = typer.Option(None, "--profile-url", help="A fully qualified URL pointing to a page representing the us"),
    external_id: str = typer.Option(None, "--external-id", help="User identifier provided by an external provisioning source."),
    display_name: str = typer.Option(None, "--display-name", help="The name displayed for the user in Webex."),
    nick_name: str = typer.Option(None, "--nick-name", help="A casual name of the user. For example, Bob when the user's"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a user with PUT\n\nExample --json-body:\n  '{"schemas":["..."],"userName":"...","userType":"user","title":"...","active":true,"roles":[{"value":"...","type":"...","display":"..."}]}'."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Users/{user_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if user_name is not None:
            body["userName"] = user_name
        if user_type is not None:
            body["userType"] = user_type
        if title is not None:
            body["title"] = title
        if active is not None:
            body["active"] = active
        if preferred_language is not None:
            body["preferredLanguage"] = preferred_language
        if locale is not None:
            body["locale"] = locale
        if timezone is not None:
            body["timezone"] = timezone
        if profile_url is not None:
            body["profileUrl"] = profile_url
        if external_id is not None:
            body["externalId"] = external_id
        if display_name is not None:
            body["displayName"] = display_name
        if nick_name is not None:
            body["nickName"] = nick_name
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("update-users")
def update_users(
    user_id: str = typer.Argument(help="userId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a user with PATCH\n\nExample --json-body:\n  '{"schemas":["..."],"Operations":[{"op":"...","path":"...","value":"..."}]}'."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Users/{user_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
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
    user_id: str = typer.Argument(help="userId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a user."""
    if not force:
        typer.confirm(f"Delete {user_id}?", abort=True)
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/identity/scim/{org_id}/v2/Users/{user_id}"
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
    typer.echo(f"Deleted: {user_id}")



@app.command("show-me")
def show_me(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Me."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/identity/scim/v2/Users/me"
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


