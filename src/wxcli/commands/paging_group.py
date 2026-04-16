import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling paging-group.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Return only paging groups with matching location ID. Default"),
    name: str = typer.Option(None, "--name", help="Return only paging groups with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Return only paging groups with matching primary phone number"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Paging Groups."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/paging"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
            items = result.get("locationPaging", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="locationPaging"))
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Enabled', 'enabled')], limit=limit)



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the paging group. Minimum length is 1. Maxim"),
    phone_number: str = typer.Option(None, "--phone-number", help="Paging group phone number. Minimum length is 1. Maximum leng"),
    extension: str = typer.Option(None, "--extension", help="Paging group extension. Minimum length is 2. Maximum length"),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name that displays when a group page is performed. Min"),
    last_name: str = typer.Option(None, "--last-name", help="Last name that displays when a group page is performed. Mini"),
    originator_caller_id_enabled: bool = typer.Option(None, "--originator-caller-id-enabled/--no-originator-caller-id-enabled", help="Determines what is shown on target users caller ID when a gr"),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="The name to be used for dial by name functions.  Characters"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Paging Group\n\nExample --json-body:\n  '{"name":"...","phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if language_code is not None:
            body["languageCode"] = language_code
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if originator_caller_id_enabled is not None:
            body["originatorCallerIdEnabled"] = originator_caller_id_enabled
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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
    location_id: str = typer.Argument(help="locationId"),
    paging_id: str = typer.Argument(help="pagingId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Paging Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging/{paging_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    location_id: str = typer.Argument(help="locationId"),
    paging_id: str = typer.Argument(help="pagingId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not the paging group is enabled."),
    name: str = typer.Option(None, "--name", help="Unique name for the paging group. Minimum length is 1. Maxim"),
    phone_number: str = typer.Option(None, "--phone-number", help="Paging group phone number. Minimum length is 1. Maximum leng"),
    extension: str = typer.Option(None, "--extension", help="Paging group extension. Minimum length is 2. Maximum length"),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name to be shown when calls are forwarded out of this"),
    last_name: str = typer.Option(None, "--last-name", help="Last name to be shown when calls are forwarded out of this p"),
    originator_caller_id_enabled: bool = typer.Option(None, "--originator-caller-id-enabled/--no-originator-caller-id-enabled", help="Determines what is shown on target users caller ID when a gr"),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name function"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Paging Group\n\nExample --json-body:\n  '{"enabled":true,"name":"...","phoneNumber":"...","extension":"...","languageCode":"...","firstName":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging/{paging_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if name is not None:
            body["name"] = name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if language_code is not None:
            body["languageCode"] = language_code
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if originator_caller_id_enabled is not None:
            body["originatorCallerIdEnabled"] = originator_caller_id_enabled
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
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
    location_id: str = typer.Argument(help="locationId"),
    paging_id: str = typer.Argument(help="pagingId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Paging Group."""
    if not force:
        typer.confirm(f"Delete {paging_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging/{paging_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
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
    typer.echo(f"Deleted: {paging_id}")



@app.command("list-available-numbers")
def list_available_numbers(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Paging Group Primary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    items = result.get("phoneNumbers", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Enabled', 'enabled')], limit=limit)


