import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling paging-group.")


@app.command("list", short_help="Read the List of Paging Groups.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Return only paging groups with matching location ID. Default is all locations"),
    name: str = typer.Option(None, "--name", help="Return only paging groups with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Return only paging groups with matching primary phone number or extension."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("locationPaging", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="locationPaging"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Phone Number', 'phoneNumber')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"...","originatorCallerIdEnabled":true,"originators":["..."],"targets":["..."],"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("create", short_help="Create a new Paging Group.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the paging group. Minimum length is 1. Maximum length is 30."),
    phone_number: str = typer.Option(None, "--phone-number", help="Paging group phone number. Minimum length is 1. Maximum length is 23. Either `phoneNumber` or `extension` is mandatory."),
    extension: str = typer.Option(None, "--extension", help="Paging group extension. Minimum length is 2. Maximum length is 10. Either `phoneNumber` or `extension` is mandatory."),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name that displays when a group page is performed. Minimum length is 1. Maximum length is 64. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Last name that displays when a group page is performed. Minimum length is 1. Maximum length is 64. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    originator_caller_id_enabled: bool = typer.Option(None, "--originator-caller-id-enabled/--no-originator-caller-id-enabled", help="Determines what is shown on target users caller ID when a group page is performed. If true shows page originator ID."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="The name to be used for dial by name functions. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Paging Group.\n\n\b\nExample: wxcli paging-group create LOCATION_ID --name NAME\n\n\b\nExample --json-body: '{"name":"...","phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"...","originatorCallerIdEnabled":true,"originators":["..."],"targets":["..."],"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show", short_help="Get Details for a Paging Group.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    paging_id: str = typer.Argument(help="Webex PAGING_GROUP id, from: wxcli paging-group list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Paging Group.\n\n\b\nExample: wxcli paging-group show LOCATION_ID PAGING_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging/{paging_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"enabled":true,"name":"...","phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"...","originatorCallerIdEnabled":true,"originators":["..."],"targets":["..."],"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("update", short_help="Update a Paging Group.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    paging_id: str = typer.Argument(help="Webex PAGING_GROUP id, from: wxcli paging-group list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not the paging group is enabled."),
    name: str = typer.Option(None, "--name", help="Unique name for the paging group. Minimum length is 1. Maximum length is 30."),
    phone_number: str = typer.Option(None, "--phone-number", help="Paging group phone number. Minimum length is 1. Maximum length is 23. Either `phoneNumber` or `extension` is mandatory."),
    extension: str = typer.Option(None, "--extension", help="Paging group extension. Minimum length is 2. Maximum length is 10. Either `phoneNumber` or `extension` is mandatory."),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name to be shown when calls are forwarded out of this paging group. Defaults to \".\". This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Last name to be shown when calls are forwarded out of this paging group. Defaults to the phone number if set, otherwise defaults to call group name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    originator_caller_id_enabled: bool = typer.Option(None, "--originator-caller-id-enabled/--no-originator-caller-id-enabled", help="Determines what is shown on target users caller ID when a group page is performed. If true shows page originator ID."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name functions. To clear the `dialByName`, the attribute must be set to null or empty string. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Paging Group.\n\n\b\nExample: wxcli paging-group update LOCATION_ID PAGING_ID\n\n\b\nExample --json-body: '{"enabled":true,"name":"...","phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"...","originatorCallerIdEnabled":true,"originators":["..."],"targets":["..."],"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging/{paging_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
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
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": paging_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Paging Group.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    paging_id: str = typer.Argument(help="Webex PAGING_GROUP id, from: wxcli paging-group list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Paging Group.\n\n\b\nExample: wxcli paging-group delete LOCATION_ID PAGING_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {paging_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/paging/{paging_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {paging_id}")
    else:
        emit({"status": "deleted", "id": paging_id}, output=output, fields=fields)



@app.command("list-available-numbers", short_help="Get Paging Group Primary Available Phone Numbers.")
def list_available_numbers(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Paging Group Primary Available Phone Numbers.\n\n\b\nExample: wxcli paging-group list-available-numbers LOCATION_ID"""
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
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Telephony Type', 'telephonyType'), ('Toll Free', 'tollFreeNumber')], limit=limit)


