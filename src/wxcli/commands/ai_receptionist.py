import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling ai-receptionist.")


@app.command("list", short_help="List AI Receptionists.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Location identifier. If not specified, returns AI receptionists from all locations."),
    name: str = typer.Option(None, "--name", help="Search AI receptionists by name (contains match)."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number or extension. Search cannot be performed based on esn."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List AI Receptionists."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/aiReceptionists"
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
            items = result.get("aiReceptionists", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="aiReceptionists"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('Routing Prefix', 'routingPrefix')], limit=limit)



_BODY_SKELETON_VALIDATE_COUNTRY = '{"countryCode":"...","locationId":"..."}'

@app.command("validate-country-for", hidden=True)
@app.command("validate-country", short_help="Validate Country for AI Receptionist.")
def validate_country(
    country_code: str = typer.Option(None, "--country-code", help="Two letter country code of the location for which AI Receptionist needs to be validated."),
    location_id: str = typer.Option(None, "--location-id", help="Location associated with the AI Receptionist."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate Country for AI Receptionist.\n\n\b\nExample: wxcli ai-receptionist validate-country --country-code COUNTRY_CODE\n\n\b\nExample --json-body: '{"countryCode":"...","locationId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_COUNTRY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/aiReceptionists/actions/validateCountry/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if country_code is not None:
            body["countryCode"] = country_code
        if location_id is not None:
            body["locationId"] = location_id
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-templates", short_help="List AI Receptionist Templates.")
def list_templates(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List AI Receptionist Templates."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/aiReceptionists/templates"
    params = {}
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
    items = result.get("templates", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("show-template", short_help="Get AI Receptionist Template Details.")
def show_template(
    template_id: str = typer.Argument(help="Webex TEMPLATE id, from: wxcli ai-receptionist list-templates"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get AI Receptionist Template Details.\n\n\b\nExample: wxcli ai-receptionist show-template TEMPLATE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/aiReceptionists/templates/{template_id}"
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



_BODY_SKELETON_VALIDATE_AI_RECEPTIONIST = '{"name":"..."}'

@app.command("validate-ai-receptionist", short_help="Validate AI Receptionist.")
def validate_ai_receptionist(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="Name of the AI Receptionist."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate AI Receptionist.\n\n\b\nExample: wxcli ai-receptionist validate-ai-receptionist LOCATION_ID --name NAME\n\n\b\nExample --json-body: '{"name":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_AI_RECEPTIONIST), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/actions/validate/invoke"
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
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-available-numbers", short_help="List Available Numbers for AI Receptionist.")
def list_available_numbers(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Search (Contains) based on number or extension. Search cannot be performed based on esn."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Numbers for AI Receptionist.\n\n\b\nExample: wxcli ai-receptionist list-available-numbers LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/availableNumbers"
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
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Telephony Type', 'telephonyType'), ('Toll Free Number', 'tollFreeNumber')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","enabled":true,"defaultAction":{"actionType":"PLAY_MESSAGE_AND_DISCONNECT","audioMessageSelection":"DEFAULT","audioFileId":"...","transferToNumber":"...","transferTo":{"contactType":"PEOPLE","contactId":"...","phoneNumber":"..."}},"aiAgent":{"voice":{"aiEngine":"PRO","displayName":"...","language":"...","languageCode":"..."},"knowledgeBaseId":"...","guidelines":{"welcomeMessage":"...","goal":"...","guideline":"..."},"transparencySettings":{"enabled":true,"message":"...","disableReason":"..."}},"phoneNumber":"...","extension":"...","directLineCallerIdName":{"directLineCallerIdNameSelection":"DISPLAY_NAME","customName":"..."},"dialByName":"..."}'

@app.command("create", short_help="Create an AI Receptionist.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="(required) Name of the AI Receptionist. This has to be unique across location."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="(required) Flag to indicate AI receptionist is enabled or not. When disabled, incoming calls to this AI receptionist will not be answered."),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number of the AI Receptionist. Either phoneNumber or extension is mandatory. At least one is required."),
    extension: str = typer.Option(None, "--extension", help="Extension of the AI Receptionist. Either phoneNumber or extension is mandatory. At least one is required."),
    direct_line_caller_id_name: str = typer.Option(None, "--direct-line-caller-id-name", help="Direct line caller ID name configuration"),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="A dial by name used for AI Receptionist name dialing. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    default_action: str = typer.Option(None, "--default-action", help="(required) Default action configuration for the AI Receptionist"),
    ai_agent: str = typer.Option(None, "--ai-agent", help="(required) AI Agent configuration"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an AI Receptionist.\n\n\b\nExample: wxcli ai-receptionist create LOCATION_ID --name NAME --enabled --default-action DEFAULT_ACTION --ai-agent AI_AGENT\n\n\b\nExample --json-body: '{"name":"...","enabled":true,"defaultAction":{"actionType":"PLAY_MESSAGE_AND_DISCONNECT","audioMessageSelection":"DEFAULT","audioFileId":"...","transferToNumber":"...","transferTo":{"contactType":"PEOPLE","contactId":"...","phoneNumber":"..."}},"aiAgent":{"voice":{"aiEngine":"PRO","displayName":"...","language":"...","languageCode":"..."},"knowledgeBaseId":"...","guidelines":{"welcomeMessage":"...","goal":"...","guideline":"..."},"transparencySettings":{"enabled":true,"message":"...","disableReason":"..."}},"phoneNumber":"...","extension":"...","directLineCallerIdName":{"directLineCallerIdNameSelection":"DISPLAY_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists"
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
        if enabled is not None:
            body["enabled"] = enabled
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if direct_line_caller_id_name is not None:
            body["directLineCallerIdName"] = direct_line_caller_id_name
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        if default_action is not None:
            body["defaultAction"] = default_action
        if ai_agent is not None:
            body["aiAgent"] = ai_agent
        _missing = [f for f in ['name', 'enabled', 'defaultAction', 'aiAgent'] if f not in body or body[f] is None]
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



@app.command("show-ai-receptionists", hidden=True)
@app.command("show", short_help="Get AI Receptionist Details.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    ai_receptionist_id: str = typer.Argument(help="Webex AI_RECEPTIONIST id, from: wxcli ai-receptionist list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get AI Receptionist Details.\n\n\b\nExample: wxcli ai-receptionist show LOCATION_ID AI_RECEPTIONIST_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/{ai_receptionist_id}"
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



_BODY_SKELETON_UPDATE = '{"name":"...","enabled":true,"phoneNumber":"...","extension":"...","alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL"}],"directLineCallerIdName":{"directLineCallerIdNameSelection":"DISPLAY_NAME","customName":"..."},"dialByName":"...","defaultAction":{"actionType":"PLAY_MESSAGE_AND_DISCONNECT","audioMessageSelection":"DEFAULT","audioFileId":"...","transferToNumber":"...","transferTo":{"contactType":"PEOPLE","contactId":"...","phoneNumber":"..."}},"aiAgent":{"voice":{"aiEngine":"PRO","displayName":"...","language":"...","languageCode":"..."},"knowledgeBaseId":"...","guidelines":{"goal":"...","welcomeMessage":"...","guideline":"..."},"transparencySettings":{"enabled":true,"message":"...","disableReason":"..."}}}'

@app.command("update", short_help="Update an AI Receptionist.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    ai_receptionist_id: str = typer.Argument(help="Webex AI_RECEPTIONIST id, from: wxcli ai-receptionist list"),
    name: str = typer.Option(None, "--name", help="Name of the AI Receptionist. This has to be unique across location."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Flag to indicate AI receptionist is enabled or not. When disabled, incoming calls to this AI receptionist will not be answered."),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number of the AI Receptionist. Either phoneNumber or extension is mandatory. At least one is required."),
    extension: str = typer.Option(None, "--extension", help="Extension of the AI Receptionist. Either phoneNumber or extension is mandatory. At least one is required."),
    direct_line_caller_id_name: str = typer.Option(None, "--direct-line-caller-id-name", help="Direct line caller ID name configuration"),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="A dial by name used for AI Receptionist name dialing. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    default_action: str = typer.Option(None, "--default-action", help="Default action configuration for the AI Receptionist"),
    ai_agent: str = typer.Option(None, "--ai-agent", help="AI Agent configuration"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an AI Receptionist.\n\n\b\nExample: wxcli ai-receptionist update LOCATION_ID AI_RECEPTIONIST_ID\n\n\b\nExample --json-body: '{"name":"...","enabled":true,"phoneNumber":"...","extension":"...","alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL"}],"directLineCallerIdName":{"directLineCallerIdNameSelection":"DISPLAY_NAME","customName":"..."},"dialByName":"...","defaultAction":{"actionType":"PLAY_MESSAGE_AND_DISCONNECT","audioMessageSelection":"DEFAULT","audioFileId":"...","transferToNumber":"...","transferTo":{"contactType":"PEOPLE","contactId":"...","phoneNumber":"..."}},"aiAgent":{"voice":{"aiEngine":"PRO","displayName":"...","language":"...","languageCode":"..."},"knowledgeBaseId":"...","guidelines":{"goal":"...","welcomeMessage":"...","guideline":"..."},"transparencySettings":{"enabled":true,"message":"...","disableReason":"..."}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/{ai_receptionist_id}"
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
        if enabled is not None:
            body["enabled"] = enabled
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if direct_line_caller_id_name is not None:
            body["directLineCallerIdName"] = direct_line_caller_id_name
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        if default_action is not None:
            body["defaultAction"] = default_action
        if ai_agent is not None:
            body["aiAgent"] = ai_agent
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": ai_receptionist_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete an AI Receptionist.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    ai_receptionist_id: str = typer.Argument(help="Webex AI_RECEPTIONIST id, from: wxcli ai-receptionist list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an AI Receptionist.\n\n\b\nExample: wxcli ai-receptionist delete LOCATION_ID AI_RECEPTIONIST_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {ai_receptionist_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/{ai_receptionist_id}"
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
        typer.echo(f"Deleted: {ai_receptionist_id}")
    else:
        emit({"status": "deleted", "id": ai_receptionist_id}, output=output, fields=fields)



@app.command("list-voices", short_help="Get AI Receptionist Voices.")
def list_voices(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get AI Receptionist Voices.\n\n\b\nExample: wxcli ai-receptionist list-voices LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/voices"
    params = {}
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
    items = result.get("aiEngines", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Name', 'name')], limit=limit)



@app.command("list-intents", short_help="List AI Receptionist Intents.")
def list_intents(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    ai_receptionist_id: str = typer.Argument(help="Webex AI_RECEPTIONIST id, from: wxcli ai-receptionist list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List AI Receptionist Intents.\n\n\b\nExample: wxcli ai-receptionist list-intents LOCATION_ID AI_RECEPTIONIST_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/{ai_receptionist_id}/intents"
    params = {}
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
    items = result.get("intents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



_BODY_SKELETON_CREATE_INTENTS = '{"name":"...","description":"...","transferTo":{"contactType":"PEOPLE","contactId":"...","phoneNumber":"..."}}'

@app.command("create-intents", short_help="Create AI Receptionist Intent.")
def create_intents(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    ai_receptionist_id: str = typer.Argument(help="Webex AI_RECEPTIONIST id, from: wxcli ai-receptionist list"),
    name: str = typer.Option(None, "--name", help="(required) Name of the intent."),
    description: str = typer.Option(None, "--description", help="(required) Description of the intent (Action)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create AI Receptionist Intent.\n\n\b\nExample: wxcli ai-receptionist create-intents LOCATION_ID AI_RECEPTIONIST_ID --json-body '{"name":"...","description":"...","transferTo":{"contactType":"PEOPLE"}}'\n\n\b\nExample --json-body: '{"name":"...","description":"...","transferTo":{"contactType":"PEOPLE","contactId":"...","phoneNumber":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_INTENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/{ai_receptionist_id}/intents"
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
        if description is not None:
            body["description"] = description
        _missing = [f for f in ['name', 'description'] if f not in body or body[f] is None]
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



@app.command("show-intents", short_help="Get AI Receptionist Intent.")
def show_intents(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    ai_receptionist_id: str = typer.Argument(help="Webex AI_RECEPTIONIST id, from: wxcli ai-receptionist list"),
    intent_id: str = typer.Argument(help="Webex INTENT id, from: wxcli ai-receptionist list-intents"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get AI Receptionist Intent.\n\n\b\nExample: wxcli ai-receptionist show-intents LOCATION_ID AI_RECEPTIONIST_ID INTENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/{ai_receptionist_id}/intents/{intent_id}"
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



_BODY_SKELETON_UPDATE_INTENTS = '{"name":"...","description":"...","transferTo":{"contactType":"PEOPLE","contactId":"...","phoneNumber":"..."}}'

@app.command("update-intents", short_help="Modify AI Receptionist Intent.")
def update_intents(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    ai_receptionist_id: str = typer.Argument(help="Webex AI_RECEPTIONIST id, from: wxcli ai-receptionist list"),
    intent_id: str = typer.Argument(help="Webex INTENT id, from: wxcli ai-receptionist list-intents"),
    name: str = typer.Option(None, "--name", help="Name of the intent."),
    description: str = typer.Option(None, "--description", help="Description of the intent (Action)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify AI Receptionist Intent.\n\n\b\nExample: wxcli ai-receptionist update-intents LOCATION_ID AI_RECEPTIONIST_ID INTENT_ID\n\n\b\nExample --json-body: '{"name":"...","description":"...","transferTo":{"contactType":"PEOPLE","contactId":"...","phoneNumber":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_INTENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/{ai_receptionist_id}/intents/{intent_id}"
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
        if description is not None:
            body["description"] = description
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": intent_id}, output=output, fields=fields)



@app.command("delete-intents", short_help="Delete AI Receptionist Intent.")
def delete_intents(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    ai_receptionist_id: str = typer.Argument(help="Webex AI_RECEPTIONIST id, from: wxcli ai-receptionist list"),
    intent_id: str = typer.Argument(help="Webex INTENT id, from: wxcli ai-receptionist list-intents"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete AI Receptionist Intent.\n\n\b\nExample: wxcli ai-receptionist delete-intents LOCATION_ID AI_RECEPTIONIST_ID INTENT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {intent_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/aiReceptionists/{ai_receptionist_id}/intents/{intent_id}"
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
        typer.echo(f"Deleted: {intent_id}")
    else:
        emit({"status": "deleted", "id": intent_id}, output=output, fields=fields)



@app.command("list-knowledge-bases", short_help="List Knowledge Bases.")
def list_knowledge_bases(
    name: str = typer.Option(None, "--name", help="Search knowledge bases by name (contains match)."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Knowledge Bases."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases"
    params = {}
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
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="knowledgeBases"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("knowledgeBases", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description'), ('Documents Count', 'documentsCount'), ('Files Count', 'filesCount')], limit=limit)



_BODY_SKELETON_CREATE_KNOWLEDGE_BASES = '{"name":"...","description":"..."}'

@app.command("create-knowledge-bases", short_help="Create a Knowledge Base.")
def create_knowledge_bases(
    name: str = typer.Option(None, "--name", help="(required) The display name assigned to the Knowledge Base. Used to identify the KB across the platform."),
    description: str = typer.Option(None, "--description", help="A human-readable description providing additional context about the purpose or contents of the Knowledge Base."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Knowledge Base.\n\n\b\nExample: wxcli ai-receptionist create-knowledge-bases --name NAME\n\n\b\nExample --json-body: '{"name":"...","description":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_KNOWLEDGE_BASES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases"
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
        if description is not None:
            body["description"] = description
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



@app.command("show-knowledge-bases", short_help="Get Knowledge Base Details.")
def show_knowledge_bases(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Knowledge Base Details.\n\n\b\nExample: wxcli ai-receptionist show-knowledge-bases KNOWLEDGE_BASE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}"
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



_BODY_SKELETON_UPDATE_KNOWLEDGE_BASES = '{"name":"...","description":"..."}'

@app.command("update-knowledge-bases", short_help="Modify a Knowledge Base.")
def update_knowledge_bases(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    name: str = typer.Option(None, "--name", help="The display name assigned to the Knowledge Base. Used to identify the KB across the platform."),
    description: str = typer.Option(None, "--description", help="A human-readable description providing additional context about the purpose or contents of the Knowledge Base."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Knowledge Base.\n\n\b\nExample: wxcli ai-receptionist update-knowledge-bases KNOWLEDGE_BASE_ID\n\n\b\nExample --json-body: '{"name":"...","description":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_KNOWLEDGE_BASES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}"
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
        if description is not None:
            body["description"] = description
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": knowledge_base_id}, output=output, fields=fields)



@app.command("delete-knowledge-bases", short_help="Delete a Knowledge Base.")
def delete_knowledge_bases(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Knowledge Base.\n\n\b\nExample: wxcli ai-receptionist delete-knowledge-bases KNOWLEDGE_BASE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {knowledge_base_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}"
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
        typer.echo(f"Deleted: {knowledge_base_id}")
    else:
        emit({"status": "deleted", "id": knowledge_base_id}, output=output, fields=fields)



@app.command("list-documents", short_help="List Knowledge Base Documents.")
def list_documents(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Knowledge Base Documents.\n\n\b\nExample: wxcli ai-receptionist list-documents KNOWLEDGE_BASE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}/documents"
    params = {}
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
            result = list(api.session.follow_pagination(url=url, params=params, item_key="documents"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("documents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Score', 'score'), ('Text', 'text')], limit=limit)



_BODY_SKELETON_CREATE_DOCUMENTS = '{"name":"...","content":"..."}'

@app.command("create-documents", short_help="Create Knowledge Base Document.")
def create_documents(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    name: str = typer.Option(None, "--name", help="(required) The display name assigned to the Knowledge Base document. Used to identify the document across the platform."),
    content: str = typer.Option(None, "--content", help="(required) The content of the document."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Knowledge Base Document.\n\n\b\nExample: wxcli ai-receptionist create-documents KNOWLEDGE_BASE_ID --name NAME --content CONTENT\n\n\b\nExample --json-body: '{"name":"...","content":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DOCUMENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}/documents"
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
        if content is not None:
            body["content"] = content
        _missing = [f for f in ['name', 'content'] if f not in body or body[f] is None]
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



@app.command("show-documents", short_help="Get Knowledge Base Document Details.")
def show_documents(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    document_id: str = typer.Argument(help="Webex KB_DOCUMENT id, from: wxcli ai-receptionist list-documents"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Knowledge Base Document Details.\n\n\b\nExample: wxcli ai-receptionist show-documents KNOWLEDGE_BASE_ID DOCUMENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}/documents/{document_id}"
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



_BODY_SKELETON_UPDATE_DOCUMENTS = '{"name":"...","content":"..."}'

@app.command("update-documents", short_help="Modify Knowledge Base Document.")
def update_documents(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    document_id: str = typer.Argument(help="Webex KB_DOCUMENT id, from: wxcli ai-receptionist list-documents"),
    name: str = typer.Option(None, "--name", help="The display name assigned to the Knowledge Base document. Used to identify the document across the platform."),
    content: str = typer.Option(None, "--content", help="The content of the document."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Knowledge Base Document.\n\n\b\nExample: wxcli ai-receptionist update-documents KNOWLEDGE_BASE_ID DOCUMENT_ID\n\n\b\nExample --json-body: '{"name":"...","content":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DOCUMENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}/documents/{document_id}"
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
        if content is not None:
            body["content"] = content
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": document_id}, output=output, fields=fields)



@app.command("delete-documents", short_help="Delete Knowledge Base Document.")
def delete_documents(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    document_id: str = typer.Argument(help="Webex KB_DOCUMENT id, from: wxcli ai-receptionist list-documents"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Knowledge Base Document.\n\n\b\nExample: wxcli ai-receptionist delete-documents KNOWLEDGE_BASE_ID DOCUMENT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {document_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}/documents/{document_id}"
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
        typer.echo(f"Deleted: {document_id}")
    else:
        emit({"status": "deleted", "id": document_id}, output=output, fields=fields)



@app.command("download-knowledge-base", hidden=True)
@app.command("download-documents", short_help="Download Knowledge Base Document.")
def download_documents(
    knowledge_base_id: str = typer.Argument(help="Webex KNOWLEDGE_BASE id, from: wxcli ai-receptionist list-knowledge-bases"),
    document_id: str = typer.Argument(help="Webex KB_DOCUMENT id, from: wxcli ai-receptionist list-documents"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Download Knowledge Base Document.\n\n\b\nExample: wxcli ai-receptionist download-documents KNOWLEDGE_BASE_ID DOCUMENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledge_base_id}/documents/{document_id}/actions/download/invoke"
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


