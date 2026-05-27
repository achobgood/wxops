import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling user-call-settings.")


@app.command("show")
def show(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Anonymous Call Rejection Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/anonymousCallReject"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
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
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Enable or disable Anonymous Call Rejection. When set to true"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Anonymous Call Rejection Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/anonymousCallReject"
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
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Enabled Calling Services for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/services"
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
    result = result or []
    items = result.get("services", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-simultaneous-ring")
def list_simultaneous_ring(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Simultaneous Ring Settings for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing"
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
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-simultaneous-ring")
def update_simultaneous_ring(
    person_id: str = typer.Argument(help="personId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="When set to `true`, simultaneous ring is enabled for this pe"),
    do_not_ring_if_on_call_enabled: bool = typer.Option(None, "--do-not-ring-if-on-call-enabled/--no-do-not-ring-if-on-call-enabled", help="When set to `true`, the configured phone numbers won't ring"),
    criterias_enabled: bool = typer.Option(None, "--criterias-enabled/--no-criterias-enabled", help="When `true`, enables the selected schedule for simultaneous"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Simultaneous Ring Settings for a Person\n\nExample --json-body:\n  '{"enabled":true,"doNotRingIfOnCallEnabled":true,"criteriasEnabled":true,"phoneNumbers":[{"phoneNumber":"...","answerConfirmationEnabled":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing"
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
        if do_not_ring_if_on_call_enabled is not None:
            body["doNotRingIfOnCallEnabled"] = do_not_ring_if_on_call_enabled
        if criterias_enabled is not None:
            body["criteriasEnabled"] = criterias_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create")
def create(
    person_id: str = typer.Argument(help="personId"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule which determines when the simultaneous"),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: LOCATION, PEOPLE"),
    calls_from: str = typer.Option(None, "--calls-from", help="(required) Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, the criteria applies to calls from anonymous ca"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, the criteria applies to calls from unavailable"),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="(required) When set to `true` simultaneous ringing is enabled for calls"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Simultaneous Ring Criteria for a Person\n\nExample --json-body:\n  '{"callsFrom":"ANY_PHONE_NUMBER","ringEnabled":true,"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"LOCATION","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing/criteria"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if ring_enabled is not None:
            body["ringEnabled"] = ring_enabled
        _missing = [f for f in ['callsFrom', 'ringEnabled'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-criteria")
def show_criteria(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Simultaneous Ring Criteria for a Person."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-criteria")
def update_criteria(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    schedule_name: str = typer.Option(None, "--schedule-name", help="Name of the schedule which determines when the simultaneous"),
    schedule_type: str = typer.Option(None, "--schedule-type", help="Choices: businessHours, holidays"),
    schedule_level: str = typer.Option(None, "--schedule-level", help="Choices: LOCATION, PEOPLE"),
    calls_from: str = typer.Option(None, "--calls-from", help="Choices: ANY_PHONE_NUMBER, SELECT_PHONE_NUMBERS"),
    anonymous_callers_enabled: bool = typer.Option(None, "--anonymous-callers-enabled/--no-anonymous-callers-enabled", help="When `true`, the criteria applies to calls from anonymous ca"),
    unavailable_callers_enabled: bool = typer.Option(None, "--unavailable-callers-enabled/--no-unavailable-callers-enabled", help="When `true`, the criteria applies to calls from unavailable"),
    ring_enabled: bool = typer.Option(None, "--ring-enabled/--no-ring-enabled", help="When set to `true` simultaneous ringing is enabled for calls"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Simultaneous Ring Criteria for a Person\n\nExample --json-body:\n  '{"scheduleName":"...","scheduleType":"businessHours","scheduleLevel":"LOCATION","callsFrom":"ANY_PHONE_NUMBER","anonymousCallersEnabled":true,"unavailableCallersEnabled":true,"phoneNumbers":["..."],"ringEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if schedule_name is not None:
            body["scheduleName"] = schedule_name
        if schedule_type is not None:
            body["scheduleType"] = schedule_type
        if schedule_level is not None:
            body["scheduleLevel"] = schedule_level
        if calls_from is not None:
            body["callsFrom"] = calls_from
        if anonymous_callers_enabled is not None:
            body["anonymousCallersEnabled"] = anonymous_callers_enabled
        if unavailable_callers_enabled is not None:
            body["unavailableCallersEnabled"] = unavailable_callers_enabled
        if ring_enabled is not None:
            body["ringEnabled"] = ring_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    person_id: str = typer.Argument(help="personId"),
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Simultaneous Ring Criteria for a Person."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/simultaneousRing/criteria/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {id}")


