import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling call-park.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Argument(help="locationId"),
    order: str = typer.Option(None, "--order", help="Sort the list of call parks by name, either ASC or DSC. Default is ASC."),
    name: str = typer.Option(None, "--name", help="Return the list of call parks that contains the given name. The maximum length is 80."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Parks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks"
    params = {}
    if order is not None:
        params["order"] = order
    if name is not None:
        params["name"] = name
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
    items = result.get("callParks", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","recall":{"option":"ALERT_PARKING_USER_ONLY","huntGroupId":"..."},"agents":["..."],"parkOnAgentsEnabled":true,"callParkExtensions":["..."]}'

@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the call park. The maximum length is 80."),
    park_on_agents_enabled: bool = typer.Option(None, "--park-on-agents-enabled/--no-park-on-agents-enabled", help="Whether or not the calls will be parked on agents as a destination."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Call Park\n\nExample --json-body:\n  '{"name":"...","recall":{"option":"ALERT_PARKING_USER_ONLY","huntGroupId":"..."},"agents":["..."],"parkOnAgentsEnabled":true,"callParkExtensions":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks"
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
        if park_on_agents_enabled is not None:
            body["parkOnAgentsEnabled"] = park_on_agents_enabled
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



@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    call_park_id: str = typer.Argument(help="callParkId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Park."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/{call_park_id}"
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



_BODY_SKELETON_UPDATE = '{"name":"...","recall":{"option":"ALERT_PARKING_USER_ONLY","huntGroupId":"..."},"agents":["..."],"parkOnAgentsEnabled":true,"callParkExtensions":["..."]}'

@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    call_park_id: str = typer.Argument(help="callParkId"),
    name: str = typer.Option(None, "--name", help="Unique name for the call park. The maximum length is 80."),
    park_on_agents_enabled: bool = typer.Option(None, "--park-on-agents-enabled/--no-park-on-agents-enabled", help="Whether or not the calls will be parked on agents as a destination."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Park\n\nExample --json-body:\n  '{"name":"...","recall":{"option":"ALERT_PARKING_USER_ONLY","huntGroupId":"..."},"agents":["..."],"parkOnAgentsEnabled":true,"callParkExtensions":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/{call_park_id}"
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
        if park_on_agents_enabled is not None:
            body["parkOnAgentsEnabled"] = park_on_agents_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("delete")
def delete(
    location_id: str = typer.Argument(help="locationId"),
    call_park_id: str = typer.Argument(help="callParkId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Park."""
    if not force:
        typer.confirm(f"Delete {call_park_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/{call_park_id}"
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
    else:
        typer.echo(f"Deleted: {call_park_id}")



@app.command("list-available-users")
def list_available_users(
    location_id: str = typer.Argument(help="locationId"),
    call_park_name: str = typer.Option(None, "--call-park-name", help="Only return available agents from call parks with the matching name."),
    name: str = typer.Option(None, "--name", help="Only return available agents with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return available agents with the matching primary number."),
    order: str = typer.Option(None, "--order", help="Order the available agents according to the designated fields. Up to three vertical bar (|) separated sort order fields may be specified. Available sort fields: fname, lname, number and extension. The maximum supported sort order value is 3."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get available agents from Call Parks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/availableUsers"
    params = {}
    if call_park_name is not None:
        params["callParkName"] = call_park_name
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
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
    items = result.get("agents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-available-recall-hunt-groups")
def list_available_recall_hunt_groups(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="Only return available recall hunt groups with the matching name."),
    order: str = typer.Option(None, "--order", help="Order the available recall hunt groups according to the designated fields. Available sort fields: lname."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get available recall hunt groups from Call Parks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/availableRecallHuntGroups"
    params = {}
    if name is not None:
        params["name"] = name
    if order is not None:
        params["order"] = order
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
    items = result.get("huntGroups", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("show-settings")
def show_settings(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Park Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/settings"
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



_BODY_SKELETON_UPDATE_SETTINGS = '{"callParkRecall":{"option":"ALERT_PARKING_USER_ONLY","huntGroupId":"..."},"callParkSettings":{"ringPattern":"NORMAL","recallTime":0,"huntWaitTime":0}}'

@app.command("update-settings")
def update_settings(
    location_id: str = typer.Argument(help="locationId"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Park settings\n\nExample --json-body:\n  '{"callParkRecall":{"option":"ALERT_PARKING_USER_ONLY","huntGroupId":"..."},"callParkSettings":{"ringPattern":"NORMAL","recallTime":0,"huntWaitTime":0}}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParks/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("list-call-park-extensions")
def list_call_park_extensions(
    location_id: str = typer.Option(None, "--location-id", help="Only return call park extensions with matching location ID."),
    extension: str = typer.Option(None, "--extension", help="Only return call park extensions with the matching extension."),
    location_name: str = typer.Option(None, "--location-name", help="Only return call park extensions with the matching extension."),
    name: str = typer.Option(None, "--name", help="Only return call park extensions with the matching name."),
    order: str = typer.Option(None, "--order", help="Order the available agents according to the designated fields. Available sort fields: `groupName`, `callParkExtension`, `callParkExtensionName`, `callParkExtensionExternalId`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Park Extensions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callParkExtensions"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if extension is not None:
        params["extension"] = extension
    if location_name is not None:
        params["locationName"] = location_name
    if name is not None:
        params["name"] = name
    if order is not None:
        params["order"] = order
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
            items = result.get("callParkExtensions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="callParkExtensions"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("show-call-park-extensions")
def show_call_park_extensions(
    location_id: str = typer.Argument(help="locationId"),
    call_park_extension_id: str = typer.Argument(help="callParkExtensionId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Park Extension."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParkExtensions/{call_park_extension_id}"
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



_BODY_SKELETON_UPDATE_CALL_PARK_EXTENSIONS = '{"name":"...","extension":"..."}'

@app.command("update-call-park-extensions")
def update_call_park_extensions(
    location_id: str = typer.Argument(help="locationId"),
    call_park_extension_id: str = typer.Argument(help="callParkExtensionId"),
    name: str = typer.Option(None, "--name", help="Name for the call park extension. The maximum length is 30."),
    extension: str = typer.Option(None, "--extension", help="Unique extension which will be assigned to call park extension. The minimum length is 2, maximum length is 10."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Park Extension\n\nExample --json-body:\n  '{"name":"...","extension":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_PARK_EXTENSIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParkExtensions/{call_park_extension_id}"
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
    else:
        typer.echo(f"Updated.")



@app.command("delete-call-park-extensions")
def delete_call_park_extensions(
    location_id: str = typer.Argument(help="locationId"),
    call_park_extension_id: str = typer.Argument(help="callParkExtensionId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Park Extension."""
    if not force:
        typer.confirm(f"Delete {call_park_extension_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParkExtensions/{call_park_extension_id}"
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
    else:
        typer.echo(f"Deleted: {call_park_extension_id}")



_BODY_SKELETON_CREATE_CALL_PARK_EXTENSIONS = '{"name":"...","extension":"..."}'

@app.command("create-call-park-extensions")
def create_call_park_extensions(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) Name for the call park extension. The maximum length is 30."),
    extension: str = typer.Option(None, "--extension", help="(required) Unique extension which will be assigned to call park extension. The minimum length is 2, maximum length is 10."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Call Park Extension\n\nExample --json-body:\n  '{"name":"...","extension":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CALL_PARK_EXTENSIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callParkExtensions"
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
        if extension is not None:
            body["extension"] = extension
        _missing = [f for f in ['name', 'extension'] if f not in body or body[f] is None]
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


