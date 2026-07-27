import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling virtual-extensions.")


@app.command("list")
def cmd_list(
    order: str = typer.Option(None, "--order", help="Order the list of virtual extensions in ascending or descending order. Default is ascending."),
    extension: str = typer.Option(None, "--extension", help="Filter the list of virtual extensions by extension number."),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter the list of virtual extensions by phone number."),
    name: str = typer.Option(None, "--name", help="Filter the list of virtual extensions by name. This can be either first name or last name."),
    location_name: str = typer.Option(None, "--location-name", help="Filter the list of virtual extensions by location name.(Only one of the locationName, locationId, and OrgLevelOnly query parameters is allowed at the same time.)"),
    location_id: str = typer.Option(None, "--location-id", help="Filter the list of virtual extensions by location ID."),
    org_level_only: str = typer.Option(None, "--org-level-only", help="Filter the list of virtual extensions by organization level. If orgLevelOnly is true, return only the organization level virtual extensions."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Virtual Extensions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensions"
    params = {}
    if order is not None:
        params["order"] = order
    if extension is not None:
        params["extension"] = extension
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if name is not None:
        params["name"] = name
    if location_name is not None:
        params["locationName"] = location_name
    if location_id is not None:
        params["locationId"] = location_id
    if org_level_only is not None:
        params["orgLevelOnly"] = org_level_only
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("virtualExtensions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'displayName'), ('Extension', 'extension'), ('Phone Number', 'phoneNumber')], limit=limit)



_BODY_SKELETON_CREATE = '{"displayName":"...","phoneNumber":"...","extension":"...","firstName":"...","lastName":"...","locationId":"..."}'

@app.command("create")
def create(
    first_name: str = typer.Option(None, "--first-name", help="First name of the person at the virtual extension."),
    last_name: str = typer.Option(None, "--last-name", help="Last name of the person at the virtual extension."),
    display_name: str = typer.Option(None, "--display-name", help="(required) Display name of the person at the virtual extension."),
    phone_number: str = typer.Option(None, "--phone-number", help="(required) Directory number of the virtual extension."),
    extension: str = typer.Option(None, "--extension", help="(required) Extension of the virtual extension."),
    location_id: str = typer.Option(None, "--location-id", help="ID of the location to which the virtual extension is assigned. The location ID is a unique identifier for the location in Webex Calling."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Virtual Extension\n\nExample --json-body:\n  '{"displayName":"...","phoneNumber":"...","extension":"...","firstName":"...","lastName":"...","locationId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensions"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if display_name is not None:
            body["displayName"] = display_name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if location_id is not None:
            body["locationId"] = location_id
        _missing = [f for f in ['displayName', 'phoneNumber', 'extension'] if f not in body or body[f] is None]
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



@app.command("show")
def show(
    extension_id: str = typer.Argument(help="extensionId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Virtual Extension."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensions/{extension_id}"
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



_BODY_SKELETON_UPDATE = '{"firstName":"...","lastName":"...","displayName":"...","phoneNumber":"...","extension":"..."}'

@app.command("update")
def update(
    extension_id: str = typer.Argument(help="extensionId"),
    first_name: str = typer.Option(None, "--first-name", help="First name of the person at the virtual extension."),
    last_name: str = typer.Option(None, "--last-name", help="Last name of the person at the virtual extension."),
    display_name: str = typer.Option(None, "--display-name", help="Display name of the person at the virtual extension."),
    phone_number: str = typer.Option(None, "--phone-number", help="Directory number of the virtual extension."),
    extension: str = typer.Option(None, "--extension", help="Extension of the virtual extension."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Virtual Extension\n\nExample --json-body:\n  '{"firstName":"...","lastName":"...","displayName":"...","phoneNumber":"...","extension":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensions/{extension_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if display_name is not None:
            body["displayName"] = display_name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
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
        emit({"status": "updated", "id": extension_id}, output=output, fields=fields)



@app.command("delete")
def delete(
    extension_id: str = typer.Argument(help="extensionId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Virtual Extension."""
    if not force:
        typer.confirm(f"Delete {extension_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensions/{extension_id}"
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
        typer.echo(f"Deleted: {extension_id}")
    else:
        emit({"status": "deleted", "id": extension_id}, output=output, fields=fields)



@app.command("show-settings")
def show_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Virtual extension settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensions/settings"
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



_BODY_SKELETON_UPDATE_SETTINGS = '{"mode":"STANDARD"}'

@app.command("update-settings")
def update_settings(
    mode: str = typer.Option(None, "--mode", help="Choices: STANDARD"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Virtual Extension Settings\n\nExample --json-body:\n  '{"mode":"STANDARD"}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensions/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if mode is not None:
            body["mode"] = mode
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
        emit({"status": "updated"}, output=output, fields=fields)



_BODY_SKELETON_VALIDATE_AN_EXTERNAL = '{"phoneNumbers":["..."]}'

@app.command("validate-an-external")
def validate_an_external(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate an external phone number\n\nExample --json-body:\n  '{"phoneNumbers":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_AN_EXTERNAL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensions/actions/validateNumbers/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-virtual-extension-ranges")
def list_virtual_extension_ranges(
    order: str = typer.Option(None, "--order", help="Sort the list of virtual extension ranges by name or prefix, either ASC or DSC. Default sort order is ASC."),
    name: str = typer.Option(None, "--name", help="Filter the list of virtual extension ranges by name."),
    prefix: str = typer.Option(None, "--prefix", help="Filter the list of virtual extension ranges by prefix."),
    location_id: str = typer.Option(None, "--location-id", help="Filter the list of virtual extension ranges by location ID. Only one of the `locationId` and `OrgLevelOnly` query parameters is allowed at the same time."),
    org_level_only: str = typer.Option(None, "--org-level-only", help="Filter the list of virtual extension ranges by organization level. If `orgLevelOnly` is true, return only the organization level virtual extension ranges."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a list of a Virtual Extension Range."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensionRanges"
    params = {}
    if order is not None:
        params["order"] = order
    if name is not None:
        params["name"] = name
    if prefix is not None:
        params["prefix"] = prefix
    if location_id is not None:
        params["locationId"] = location_id
    if org_level_only is not None:
        params["orgLevelOnly"] = org_level_only
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("virtualExtensionRanges", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE_VIRTUAL_EXTENSION_RANGES = '{"name":"...","prefix":"...","patterns":["..."],"locationId":"..."}'

@app.command("create-virtual-extension-ranges")
def create_virtual_extension_ranges(
    name: str = typer.Option(None, "--name", help="(required) Name of the virtual extension range. This is a unique name for the virtual extension range."),
    prefix: str = typer.Option(None, "--prefix", help="(required) Prefix used for a virtual extension range. Prefix works in Standard and Enhanced modes. In Standard mode, it must be E.164 and unique. In Enhanced mode, it can be E.164 or non-E.164."),
    location_id: str = typer.Option(None, "--location-id", help="ID of the location to which the virtual extension range is assigned. The location ID is a unique identifier for the location in Webex Calling. This is set only when location level virtual extension range is added."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Virtual Extension Range\n\nExample --json-body:\n  '{"name":"...","prefix":"...","patterns":["..."],"locationId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_VIRTUAL_EXTENSION_RANGES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensionRanges"
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
        if prefix is not None:
            body["prefix"] = prefix
        if location_id is not None:
            body["locationId"] = location_id
        _missing = [f for f in ['name', 'prefix'] if f not in body or body[f] is None]
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



@app.command("show-virtual-extension-ranges")
def show_virtual_extension_ranges(
    extension_range_id: str = typer.Argument(help="extensionRangeId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get details of a Virtual Extension Range."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensionRanges/{extension_range_id}"
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



_BODY_SKELETON_UPDATE_VIRTUAL_EXTENSION_RANGES = '{"name":"...","prefix":"...","patterns":["..."],"action":"ADD"}'

@app.command("update-virtual-extension-ranges")
def update_virtual_extension_ranges(
    extension_range_id: str = typer.Argument(help="extensionRangeId"),
    name: str = typer.Option(None, "--name", help="Name of the virtual extension range. This is a unique name for the virtual extension range."),
    prefix: str = typer.Option(None, "--prefix", help="Prefix used for a virtual extension range."),
    action: str = typer.Option(None, "--action", help="Choices: ADD, REMOVE, REPLACE"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Virtual Extension Range\n\nExample --json-body:\n  '{"name":"...","prefix":"...","patterns":["..."],"action":"ADD"}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VIRTUAL_EXTENSION_RANGES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensionRanges/{extension_range_id}"
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
        if prefix is not None:
            body["prefix"] = prefix
        if action is not None:
            body["action"] = action
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
        emit({"status": "updated", "id": extension_range_id}, output=output, fields=fields)



@app.command("delete-virtual-extension-ranges")
def delete_virtual_extension_ranges(
    extension_range_id: str = typer.Argument(help="extensionRangeId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Virtual Extension Range."""
    if not force:
        typer.confirm(f"Delete {extension_range_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensionRanges/{extension_range_id}"
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
        typer.echo(f"Deleted: {extension_range_id}")
    else:
        emit({"status": "deleted", "id": extension_range_id}, output=output, fields=fields)



_BODY_SKELETON_VALIDATE_THE_PREFIX = '{"locationId":"...","name":"...","prefix":"...","patterns":["..."],"rangeId":"..."}'

@app.command("validate-the-prefix")
def validate_the_prefix(
    location_id: str = typer.Option(None, "--location-id", help="ID of the location to which the virtual extension range is assigned. The location ID is a unique identifier for the location in Webex Calling."),
    name: str = typer.Option(None, "--name", help="Name of the virtual extension range. This is a unique name for the virtual extension range."),
    prefix: str = typer.Option(None, "--prefix", help="Prefix used for a virtual extension range."),
    range_id: str = typer.Option(None, "--range-id", help="ID of the virtual extension range. This is mandatory when validating for an existing virtual extension range, not present when validating a new virtual extension range before adding it."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate the prefix and extension pattern for a Virtual Extension Range\n\nExample --json-body:\n  '{"locationId":"...","name":"...","prefix":"...","patterns":["..."],"rangeId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_THE_PREFIX), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualExtensionRanges/actions/validate/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if location_id is not None:
            body["locationId"] = location_id
        if name is not None:
            body["name"] = name
        if prefix is not None:
            body["prefix"] = prefix
        if range_id is not None:
            body["rangeId"] = range_id
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


