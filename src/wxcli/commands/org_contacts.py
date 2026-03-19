import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling organization-contacts.")


@app.command("create")
def create(
    org_id: str = typer.Argument(help="orgId"),
    schemas: str = typer.Option(..., "--schemas", help="\"urn:cisco:codev:identity:contact:core:1.0\"."),
    display_name: str = typer.Option(None, "--display-name", help="The full name of the contact."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the contact."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the contact."),
    company_name: str = typer.Option(None, "--company-name", help="The company the contact is working for."),
    title: str = typer.Option(None, "--title", help="The contact's title."),
    address: str = typer.Option(None, "--address", help="Contact's address."),
    avatar_url: str = typer.Option(None, "--avatar-url", help="The URL to the person's avatar in PNG format."),
    primary_contact_method: str = typer.Option(None, "--primary-contact-method", help="Choices: SIPADDRESS, EMAIL, PHONE, IMS"),
    source: str = typer.Option(..., "--source", help="Choices: CH, Webex4Broadworks"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Contact."""
    api = get_api(debug=debug)
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
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "contactId" in result:
        typer.echo(f"Created: {result['contactId']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show")
def show(
    org_id: str = typer.Argument(help="orgId"),
    contact_id: str = typer.Argument(help="contactId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Contact."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/{contact_id}"
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
    org_id: str = typer.Argument(help="orgId"),
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
    """Update a Contact."""
    api = get_api(debug=debug)
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
    org_id: str = typer.Argument(help="orgId"),
    contact_id: str = typer.Argument(help="contactId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Contact."""
    if not force:
        typer.confirm(f"Delete {contact_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/{contact_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {contact_id}")



@app.command("list")
def cmd_list(
    org_id: str = typer.Argument(help="orgId"),
    keyword: str = typer.Option(None, "--keyword", help="List contacts with a keyword."),
    source: str = typer.Option(None, "--source", help="List contacts with source."),
    limit: str = typer.Option(None, "--limit", help="Limit the maximum number of contact in the response."),
    group_ids: str = typer.Option(None, "--group-ids", help="Filter contacts based on groups."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contacts."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/search"
    params = {}
    if keyword is not None:
        params["keyword"] = keyword
    if source is not None:
        params["source"] = source
    if limit is not None:
        params["limit"] = limit
    if group_ids is not None:
        params["groupIds"] = group_ids
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
    items = result.get("result", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=0)



@app.command("create-bulk")
def create_bulk(
    org_id: str = typer.Argument(help="orgId"),
    schemas: str = typer.Option(..., "--schemas", help="\"urn:cisco:codev:identity:contact:core:1.0\"."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk Create or Update Contacts."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schemas is not None:
            body["schemas"] = schemas
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



@app.command("create-delete")
def create_delete(
    org_id: str = typer.Argument(help="orgId"),
    schemas: str = typer.Option(..., "--schemas", help="\"urn:cisco:codev:identity:contact:core:1.0\"."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk Delete Contacts."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/bulk/delete"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schemas is not None:
            body["schemas"] = schemas
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


