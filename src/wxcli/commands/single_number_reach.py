import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling single-number-reach.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Argument(help="locationId"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Single Number Reach Primary Available Phone Numbers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/singleNumberReach/availableNumbers"
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
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state')], limit=limit)



_BODY_SKELETON_CREATE = '{"phoneNumber":"...","enabled":true,"name":"...","doNotForwardCallsEnabled":true,"answerConfirmationEnabled":true}'

@app.command("create")
def create(
    person_id: str = typer.Argument(help="personId"),
    phone_number: str = typer.Option(None, "--phone-number", help="(required) Personal phone number used as single Number Reach."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="(required) A flag to enable or disable single Number Reach."),
    name: str = typer.Option(None, "--name", help="(required) Name of the single number reach phone number entry."),
    do_not_forward_calls_enabled: bool = typer.Option(None, "--do-not-forward-calls-enabled/--no-do-not-forward-calls-enabled", help="If enabled, the call forwarding settings of provided phone Number will not be applied."),
    answer_confirmation_enabled: bool = typer.Option(None, "--answer-confirmation-enabled/--no-answer-confirmation-enabled", help="If enabled, the call recepient will be prompted to press a key before being connected."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Single Number Reach For a Person\n\nExample --json-body:\n  '{"phoneNumber":"...","enabled":true,"name":"...","doNotForwardCallsEnabled":true,"answerConfirmationEnabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/singleNumberReach/numbers"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if enabled is not None:
            body["enabled"] = enabled
        if name is not None:
            body["name"] = name
        if do_not_forward_calls_enabled is not None:
            body["doNotForwardCallsEnabled"] = do_not_forward_calls_enabled
        if answer_confirmation_enabled is not None:
            body["answerConfirmationEnabled"] = answer_confirmation_enabled
        _missing = [f for f in ['phoneNumber', 'enabled', 'name'] if f not in body or body[f] is None]
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



@app.command("list-single-number-reach")
def list_single_number_reach(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Single Number Reach Settings For A Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/singleNumberReach"
    params = {}
    if limit > 0:
        params["max"] = limit
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
    items = result.get("numbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Phone Number', 'phoneNumber'), ('Enabled', 'enabled'), ('Do Not Forward Calls Enabled', 'doNotForwardCallsEnabled')], limit=limit)



_BODY_SKELETON_UPDATE = '{"alertAllNumbersForClickToDialCallsEnabled":true}'

@app.command("update")
def update(
    person_id: str = typer.Argument(help="personId"),
    alert_all_numbers_for_click_to_dial_calls_enabled: bool = typer.Option(None, "--alert-all-numbers-for-click-to-dial-calls-enabled/--no-alert-all-numbers-for-click-to-dial-calls-enabled", help="Flag to enable alerting single number reach numbers for click to dial calls."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Single Number Reach Settings For A Person\n\nExample --json-body:\n  '{"alertAllNumbersForClickToDialCallsEnabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/singleNumberReach"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if alert_all_numbers_for_click_to_dial_calls_enabled is not None:
            body["alertAllNumbersForClickToDialCallsEnabled"] = alert_all_numbers_for_click_to_dial_calls_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_NUMBERS = '{"phoneNumber":"...","enabled":true,"name":"...","doNotForwardCallsEnabled":true,"answerConfirmationEnabled":true}'

@app.command("update-numbers")
def update_numbers(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    phone_number: str = typer.Option(None, "--phone-number", help="Personal phone number used as single Number Reach."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="A flag to enable or disable single Number Reach phone number."),
    name: str = typer.Option(None, "--name", help="Name of the single number reach phone number entry."),
    do_not_forward_calls_enabled: bool = typer.Option(None, "--do-not-forward-calls-enabled/--no-do-not-forward-calls-enabled", help="If enabled, the call forwarding settings of provided phone Number will not be applied."),
    answer_confirmation_enabled: bool = typer.Option(None, "--answer-confirmation-enabled/--no-answer-confirmation-enabled", help="If enabled, the call recepient will be prompted to press a key before being connected."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Single Number Reach Settings For A Number\n\nExample --json-body:\n  '{"phoneNumber":"...","enabled":true,"name":"...","doNotForwardCallsEnabled":true,"answerConfirmationEnabled":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/singleNumberReach/numbers/{id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if enabled is not None:
            body["enabled"] = enabled
        if name is not None:
            body["name"] = name
        if do_not_forward_calls_enabled is not None:
            body["doNotForwardCallsEnabled"] = do_not_forward_calls_enabled
        if answer_confirmation_enabled is not None:
            body["answerConfirmationEnabled"] = answer_confirmation_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete")
def delete(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete A Single Number Reach Number."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/singleNumberReach/numbers/{id}"
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
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)


