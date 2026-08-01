import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling org-contacts.")


_BODY_SKELETON_CREATE = '{"schemas":"...","source":"CH","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"...","address":"...","avatarURL":"...","primaryContactMethod":"SIPADDRESS","emails":[{"value":"...","type":"work","primary":true}],"phoneNumbers":[{"value":"...","type":"work","primary":true}],"sipAddresses":[{"value":"...","type":"enterprise","primary":true}],"ims":[{"value":"...","type":"aim","primary":true}],"groupIds":["..."]}'

@app.command("create", short_help="Create a Contact.")
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
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Contact.\n\n\b\nExample: wxcli org-contacts create --schemas SCHEMAS --source CH\n\n\b\nExample --json-body: '{"schemas":"...","source":"CH","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"...","address":"...","avatarURL":"...","primaryContactMethod":"SIPADDRESS","emails":[{"value":"...","type":"work","primary":true}],"phoneNumbers":[{"value":"...","type":"work","primary":true}],"sipAddresses":[{"value":"...","type":"enterprise","primary":true}],"ims":[{"value":"...","type":"aim","primary":true}],"groupIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts"
    if json_body:
        body = load_json_body(json_body)
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
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "contactId" in result:
            typer.echo(f"Created: {result['contactId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("show", short_help="Get a Contact.")
def show(
    contact_id: str = typer.Argument(help="UUID"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Contact.\n\n\b\nExample: wxcli org-contacts show CONTACT_ID"""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/{contact_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"schemas":"...","source":"CH","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"...","address":"...","avatarURL":"...","primaryContactMethod":"SIPADDRESS","emails":[{"value":"...","type":"work","primary":true}],"phoneNumbers":[{"value":"...","type":"work","primary":true,"operation":"..."}],"sipAddresses":[{"value":"...","type":"enterprise","primary":true}],"ims":[{"value":"...","type":"aim","primary":true}],"groupIds":["..."]}'

@app.command("update", short_help="Update a Contact.")
def update(
    contact_id: str = typer.Argument(help="UUID"),
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
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Contact.\n\n\b\nExample: wxcli org-contacts update CONTACT_ID --schemas SCHEMAS --source CH\n\n\b\nExample --json-body: '{"schemas":"...","source":"CH","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"...","address":"...","avatarURL":"...","primaryContactMethod":"SIPADDRESS","emails":[{"value":"...","type":"work","primary":true}],"phoneNumbers":[{"value":"...","type":"work","primary":true,"operation":"..."}],"sipAddresses":[{"value":"...","type":"enterprise","primary":true}],"ims":[{"value":"...","type":"aim","primary":true}],"groupIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/{contact_id}"
    if json_body:
        body = load_json_body(json_body)
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
        emit({"status": "updated", "id": contact_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Contact.")
def delete(
    contact_id: str = typer.Argument(help="UUID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Contact.\n\n\b\nExample: wxcli org-contacts delete CONTACT_ID"""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {contact_id}?", abort=True)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/{contact_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {contact_id}")
    else:
        emit({"status": "deleted", "id": contact_id}, output=output, fields=fields)



@app.command("list", short_help="List Contacts.")
def cmd_list(
    keyword: str = typer.Option(None, "--keyword", help="List contacts with a keyword."),
    source: str = typer.Option(None, "--source", help="List contacts with source."),
    group_ids: str = typer.Option(None, "--group-ids", help="Filter contacts based on groups."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("result", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Contact ID', 'contactId'), ('Display Name', 'displayName'), ('Schemas', 'schemas'), ('First Name', 'firstName'), ('Last Name', 'lastName')], limit=limit)



_BODY_SKELETON_CREATE_BULK = '{"schemas":"...","contacts":[{"source":"CH","contactId":"...","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"...","address":"...","avatarURL":"...","primaryContactMethod":"SIPADDRESS","emails":[{"value":"...","type":"work","primary":true}],"phoneNumbers":[{"value":"...","type":"work","primary":true}],"sipAddresses":[{"value":"...","type":"enterprise","primary":true}],"ims":[{"value":"...","type":"aim","primary":true}]}]}'

@app.command("create-bulk", short_help="Bulk Create or Update Contacts.")
def create_bulk(
    schemas: str = typer.Option(None, "--schemas", help="(required) \"urn:cisco:codev:identity:contact:core:1.0\"."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk Create or Update Contacts.\n\n\b\nExample: wxcli org-contacts create-bulk --json-body '{"schemas":"...","contacts":[{"source":"CH"}]}'\n\n\b\nExample --json-body: '{"schemas":"...","contacts":[{"source":"CH","contactId":"...","displayName":"...","firstName":"...","lastName":"...","companyName":"...","title":"...","address":"...","avatarURL":"...","primaryContactMethod":"SIPADDRESS","emails":[{"value":"...","type":"work","primary":true}],"phoneNumbers":[{"value":"...","type":"work","primary":true}],"sipAddresses":[{"value":"...","type":"enterprise","primary":true}],"ims":[{"value":"...","type":"aim","primary":true}]}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/bulk"
    if json_body:
        body = load_json_body(json_body)
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



_BODY_SKELETON_CREATE_DELETE = '{"schemas":"...","objectIds":["..."]}'

@app.command("create-delete", short_help="Bulk Delete Contacts.")
def create_delete(
    schemas: str = typer.Option(None, "--schemas", help="(required) \"urn:cisco:codev:identity:contact:core:1.0\"."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk Delete Contacts.\n\n\b\nExample: wxcli org-contacts create-delete --json-body '{"schemas":"...","objectIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DELETE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/v1/contacts/organizations/{org_id}/contacts/bulk/delete"
    if json_body:
        body = load_json_body(json_body)
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


