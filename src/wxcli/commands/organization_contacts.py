import json
import typer
from wxcli.errors import WebexError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Calling organization-contacts.")


@app.command("create")
def create(
    schemas: str = typer.Option(None, "--schemas", help="(required) \"urn:cisco:codev:identity:contact:core:1.0\"."),
    display_name: str = typer.Option(None, "--display-name", help="The full name of the contact."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the contact."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the contact."),
    company_name: str = typer.Option(None, "--company-name", help="The company the contact is working for."),
    title: str = typer.Option(None, "--title", help="The contact's title."),
    address: str = typer.Option(None, "--address", help="Contact's address."),
    avatar_url: str = typer.Option(None, "--avatar-url", help="The URL to the person's avatar in PNG format."),
    primary_contact_method: str = typer.Option(None, "--primary-contact-method", help="Choices: SIPADDRESS, EMAIL, PHONE, IMS"),
    source: str = typer.Option(None, "--source", help="(required) Choices: CH, Webex4Broadworks"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Contact\n\nExample --json-body:\n  '{"schemas":"...","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"..."}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schemas is not None:
            body["schemas"] = schemas
        if display_name is not None:
            body["displayName"] = display_name
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if company_name is not None:
            body["companyName"] = company_name
        if title is not None:
            body["title"] = title
        if address is not None:
            body["address"] = address
        if avatar_url is not None:
            body["avatarURL"] = avatar_url
        if primary_contact_method is not None:
            body["primaryContactMethod"] = primary_contact_method
        if source is not None:
            body["source"] = source
        _missing = [f for f in ['schemas', 'source'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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
    elif isinstance(result, dict) and "contactId" in result:
        typer.echo(f"Created: {result['contactId']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show")
def show(
    contact_id: str = typer.Argument(help="contactId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Contact."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/{contact_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
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
    contact_id: str = typer.Argument(help="contactId"),
    schemas: str = typer.Option(None, "--schemas", help="\"urn:cisco:codev:identity:contact:core:1.0\"."),
    display_name: str = typer.Option(None, "--display-name", help="The full name of the contact."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the contact."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the contact."),
    company_name: str = typer.Option(None, "--company-name", help="The company the contact is working for."),
    title: str = typer.Option(None, "--title", help="The contact's title."),
    address: str = typer.Option(None, "--address", help="Contact's address."),
    avatar_url: str = typer.Option(None, "--avatar-url", help="The URL to the person's avatar in PNG format."),
    primary_contact_method: str = typer.Option(None, "--primary-contact-method", help="Choices: SIPADDRESS, EMAIL, PHONE, IMS"),
    source: str = typer.Option(None, "--source", help="Choices: CH, Webex4Broadworks"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Contact\n\nExample --json-body:\n  '{"schemas":"...","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"..."}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/{contact_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schemas is not None:
            body["schemas"] = schemas
        if display_name is not None:
            body["displayName"] = display_name
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if company_name is not None:
            body["companyName"] = company_name
        if title is not None:
            body["title"] = title
        if address is not None:
            body["address"] = address
        if avatar_url is not None:
            body["avatarURL"] = avatar_url
        if primary_contact_method is not None:
            body["primaryContactMethod"] = primary_contact_method
        if source is not None:
            body["source"] = source
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
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
    contact_id: str = typer.Argument(help="contactId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Contact."""
    if not force:
        typer.confirm(f"Delete {contact_id}?", abort=True)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/{contact_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
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
    typer.echo(f"Deleted: {contact_id}")



@app.command("list")
def cmd_list(
    keyword: str = typer.Option(None, "--keyword", help="List contacts with a keyword."),
    source: str = typer.Option(None, "--source", help="List contacts with source."),
    group_ids: str = typer.Option(None, "--group-ids", help="Filter contacts based on groups."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contacts."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/search"
    params = {}
    if keyword is not None:
        params["keyword"] = keyword
    if source is not None:
        params["source"] = source
    if group_ids is not None:
        params["groupIds"] = group_ids
    if limit > 0:
        params["limit"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    items = result.get("result", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-bulk")
def create_bulk(
    schemas: str = typer.Option(None, "--schemas", help="(required) \"urn:cisco:codev:identity:contact:core:1.0\"."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk Create or Update Contacts\n\nExample --json-body:\n  '{"schemas":"...","contacts":[{"contactId":"...","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"..."}]}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schemas is not None:
            body["schemas"] = schemas
        _missing = [f for f in ['schemas'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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



@app.command("create-delete")
def create_delete(
    schemas: str = typer.Option(None, "--schemas", help="(required) \"urn:cisco:codev:identity:contact:core:1.0\"."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk Delete Contacts\n\nExample --json-body:\n  '{"schemas":"...","objectIds":["..."]}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/bulk/delete"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schemas is not None:
            body["schemas"] = schemas
        _missing = [f for f in ['schemas'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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


