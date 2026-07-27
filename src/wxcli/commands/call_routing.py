import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling call-routing.")


_BODY_SKELETON_TEST_CALL_ROUTING = '{"originatorId":"...","originatorType":"PEOPLE","destination":"...","originatorNumber":"...","includeAppliedServices":true}'

@app.command("test-call-routing")
def test_call_routing(
    originator_id: str = typer.Option(None, "--originator-id", help="This element is used to identify the originating party. It can be a person ID or a trunk ID."),
    originator_type: str = typer.Option(None, "--originator-type", help="Choices: PEOPLE, TRUNK"),
    originator_number: str = typer.Option(None, "--originator-number", help="Only used when `originatorType` is `TRUNK`. The `originatorNumber` can be a phone number or URI."),
    destination: str = typer.Option(None, "--destination", help="This element specifies the called party. It can be any dialable string, for example, an ESN number, E.164 number, hosted user DN, extension, extension with location code, URL, or FAC code."),
    include_applied_services: str = typer.Option(None, "--include-applied-services", help="This element is used to retrieve if any translation pattern, call intercept, permission by type or permission by digit pattern is present for the called party."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Test Call Routing\n\nExample --json-body:\n  '{"originatorId":"...","originatorType":"PEOPLE","destination":"...","originatorNumber":"...","includeAppliedServices":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_TEST_CALL_ROUTING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/actions/testCallRouting/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if originator_id is not None:
            body["originatorId"] = originator_id
        if originator_type is not None:
            body["originatorType"] = originator_type
        if originator_number is not None:
            body["originatorNumber"] = originator_number
        if destination is not None:
            body["destination"] = destination
        if include_applied_services is not None:
            body["includeAppliedServices"] = include_applied_services
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list")
def cmd_list(
    trunk_id: str = typer.Argument(help="trunkId"),
    order: str = typer.Option(None, "--order", help="Order the trunks according to the designated fields. Available sort fields are `name`, and `locationName`. Sort order is ascending by default"),
    name: str = typer.Option(None, "--name", help="Return the list of trunks matching the local gateway names"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Local Gateway Dial Plan Usage for a Trunk."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/{trunk_id}/usageDialPlan"
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
    items = result.get("dialPlans", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-usage-pstn-connection-trunks")
def list_usage_pstn_connection_trunks(
    trunk_id: str = typer.Argument(help="trunkId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Locations Using the Local Gateway as PSTN Connection Routing."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/{trunk_id}/usagePstnConnection"
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
    items = result.get("locations", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-usage-route-group")
def list_usage_route_group(
    trunk_id: str = typer.Argument(help="trunkId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Route Groups Using the Local Gateway."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/{trunk_id}/usageRouteGroup"
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
    items = result.get("routeGroup", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('In Use', 'inUse')], limit=limit)



@app.command("show")
def show(
    trunk_id: str = typer.Argument(help="trunkId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Local Gateway Usage Count."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/{trunk_id}/usage"
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



_BODY_SKELETON_UPDATE = '{"dialPatterns":[{"dialPattern":"...","action":"..."}],"deleteAllDialPatterns":true}'

@app.command("update")
def update(
    dial_plan_id: str = typer.Argument(help="dialPlanId"),
    delete_all_dial_patterns: bool = typer.Option(None, "--delete-all-dial-patterns/--no-delete-all-dial-patterns", help="Delete all the dial patterns for a dial plan."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Dial Patterns\n\nExample --json-body:\n  '{"dialPatterns":[{"dialPattern":"...","action":"..."}],"deleteAllDialPatterns":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/dialPlans/{dial_plan_id}/dialPatterns"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if delete_all_dial_patterns is not None:
            body["deleteAllDialPatterns"] = delete_all_dial_patterns
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
        emit({"status": "updated", "id": dial_plan_id}, output=output, fields=fields)



_BODY_SKELETON_VALIDATE_A_DIAL = '{"dialPatterns":["..."]}'

@app.command("validate-a-dial")
def validate_a_dial(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate a Dial Pattern\n\nExample --json-body:\n  '{"dialPatterns":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_A_DIAL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/actions/validateDialPatterns/invoke"
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



@app.command("list-dial-plans")
def list_dial_plans(
    dial_plan_name: str = typer.Option(None, "--dial-plan-name", help="Return the list of dial plans matching the dial plan name."),
    route_group_name: str = typer.Option(None, "--route-group-name", help="Return the list of dial plans matching the Route group name.."),
    trunk_name: str = typer.Option(None, "--trunk-name", help="Return the list of dial plans matching the Trunk name.."),
    order: str = typer.Option(None, "--order", help="Order the dial plans according to the designated fields. Available sort fields: `name`, `routeName`, `routeType`. Sort order is ascending by default"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Dial Plans."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/dialPlans"
    params = {}
    if dial_plan_name is not None:
        params["dialPlanName"] = dial_plan_name
    if route_group_name is not None:
        params["routeGroupName"] = route_group_name
    if trunk_name is not None:
        params["trunkName"] = trunk_name
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
    items = result.get("dialPlans", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","routeId":"...","routeType":"ROUTE_GROUP","dialPatterns":["..."]}'

@app.command("create")
def create(
    name: str = typer.Option(None, "--name", help="(required) A unique name for the dial plan."),
    route_id: str = typer.Option(None, "--route-id", help="(required) ID of route type associated with the dial plan."),
    route_type: str = typer.Option(None, "--route-type", help="(required) Choices: ROUTE_GROUP, TRUNK"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Dial Plan\n\nExample --json-body:\n  '{"name":"...","routeId":"...","routeType":"ROUTE_GROUP","dialPatterns":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/dialPlans"
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
        if route_id is not None:
            body["routeId"] = route_id
        if route_type is not None:
            body["routeType"] = route_type
        _missing = [f for f in ['name', 'routeId', 'routeType'] if f not in body or body[f] is None]
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



@app.command("show-dial-plans")
def show_dial_plans(
    dial_plan_id: str = typer.Argument(help="dialPlanId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Dial Plan."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/dialPlans/{dial_plan_id}"
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



_BODY_SKELETON_UPDATE_DIAL_PLANS = '{"name":"...","routeId":"...","routeType":"ROUTE_GROUP"}'

@app.command("update-dial-plans")
def update_dial_plans(
    dial_plan_id: str = typer.Argument(help="dialPlanId"),
    name: str = typer.Option(None, "--name", help="A unique name for the dial plan."),
    route_id: str = typer.Option(None, "--route-id", help="ID of route type associated with the dial plan."),
    route_type: str = typer.Option(None, "--route-type", help="Choices: ROUTE_GROUP, TRUNK"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Dial Plan\n\nExample --json-body:\n  '{"name":"...","routeId":"...","routeType":"ROUTE_GROUP"}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DIAL_PLANS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/dialPlans/{dial_plan_id}"
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
        if route_id is not None:
            body["routeId"] = route_id
        if route_type is not None:
            body["routeType"] = route_type
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
        emit({"status": "updated", "id": dial_plan_id}, output=output, fields=fields)



@app.command("delete")
def delete(
    dial_plan_id: str = typer.Argument(help="dialPlanId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Dial Plan."""
    if not force:
        typer.confirm(f"Delete {dial_plan_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/dialPlans/{dial_plan_id}"
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
        typer.echo(f"Deleted: {dial_plan_id}")
    else:
        emit({"status": "deleted", "id": dial_plan_id}, output=output, fields=fields)



_BODY_SKELETON_VALIDATE_LOCAL_GATEWAY = '{"address":"...","domain":"...","port":0}'

@app.command("validate-local-gateway")
def validate_local_gateway(
    address: str = typer.Option(None, "--address", help="FQDN or SRV address of the trunk."),
    domain: str = typer.Option(None, "--domain", help="Domain name of the trunk."),
    port: str = typer.Option(None, "--port", help="FQDN port of the trunk."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate Local Gateway FQDN and Domain for a Trunk\n\nExample --json-body:\n  '{"address":"...","domain":"...","port":0}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VALIDATE_LOCAL_GATEWAY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/actions/fqdnValidation/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if address is not None:
            body["address"] = address
        if domain is not None:
            body["domain"] = domain
        if port is not None:
            body["port"] = port
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-trunks")
def list_trunks(
    name: str = typer.Option(None, "--name", help="Return the list of trunks matching the local gateway names."),
    location_name: str = typer.Option(None, "--location-name", help="Return the list of trunks matching the location names."),
    trunk_type: str = typer.Option(None, "--trunk-type", help="Return the list of trunks matching the trunk type."),
    order: str = typer.Option(None, "--order", help="Order the trunks according to the designated fields. Available sort fields: name, locationName. Sort order is ascending by default"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Trunks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks"
    params = {}
    if name is not None:
        params["name"] = name
    if location_name is not None:
        params["locationName"] = location_name
    if trunk_type is not None:
        params["trunkType"] = trunk_type
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
    items = result.get("trunks", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Trunk Type', 'trunkType')], limit=limit)



_BODY_SKELETON_CREATE_TRUNKS = '{"name":"...","locationId":"...","password":"...","trunkType":"REGISTERING","dualIdentitySupportEnabled":true,"deviceType":"...","address":"...","domain":"..."}'

@app.command("create-trunks")
def create_trunks(
    name: str = typer.Option(None, "--name", help="(required) A unique name for the trunk."),
    location_id: str = typer.Option(None, "--location-id", help="(required) ID of location associated with the trunk."),
    password: str = typer.Option(None, "--password", help="(required) A password to use on the trunk."),
    dual_identity_support_enabled: bool = typer.Option(None, "--dual-identity-support-enabled/--no-dual-identity-support-enabled", help="Dual Identity Support setting impacts the handling of the From header and P-Asserted-Identity header when sending an initial SIP `INVITE` to the trunk for an outbound call."),
    trunk_type: str = typer.Option(None, "--trunk-type", help="(required) Choices: REGISTERING, CERTIFICATE_BASED"),
    device_type: str = typer.Option(None, "--device-type", help="Device type assosiated with trunk."),
    address: str = typer.Option(None, "--address", help="FQDN or SRV address. Required to create a static certificate-based trunk."),
    domain: str = typer.Option(None, "--domain", help="Domain name. Required to create a static certificate based trunk."),
    port: str = typer.Option(None, "--port", help="FQDN port. Required to create a static certificate-based trunk."),
    max_concurrent_calls: str = typer.Option(None, "--max-concurrent-calls", help="Max Concurrent call. Required to create a static certificate based trunk."),
    p_charge_info_support_policy: str = typer.Option(None, "--p-charge-info-support-policy", help="Choices: DISABLED, ASSERTED_IDENTITY, CONFIGURABLE_CHARGE_NUMBER"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Trunk\n\nExample --json-body:\n  '{"name":"...","locationId":"...","password":"...","trunkType":"REGISTERING","dualIdentitySupportEnabled":true,"deviceType":"...","address":"...","domain":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TRUNKS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks"
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
        if location_id is not None:
            body["locationId"] = location_id
        if password is not None:
            body["password"] = password
        if dual_identity_support_enabled is not None:
            body["dualIdentitySupportEnabled"] = dual_identity_support_enabled
        if trunk_type is not None:
            body["trunkType"] = trunk_type
        if device_type is not None:
            body["deviceType"] = device_type
        if address is not None:
            body["address"] = address
        if domain is not None:
            body["domain"] = domain
        if port is not None:
            body["port"] = port
        if max_concurrent_calls is not None:
            body["maxConcurrentCalls"] = max_concurrent_calls
        if p_charge_info_support_policy is not None:
            body["pChargeInfoSupportPolicy"] = p_charge_info_support_policy
        _missing = [f for f in ['name', 'locationId', 'password', 'trunkType'] if f not in body or body[f] is None]
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



@app.command("show-trunks")
def show_trunks(
    trunk_id: str = typer.Argument(help="trunkId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Trunk."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/{trunk_id}"
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



_BODY_SKELETON_UPDATE_TRUNKS = '{"name":"...","password":"...","dualIdentitySupportEnabled":true,"maxConcurrentCalls":0,"pChargeInfoSupportPolicy":"DISABLED"}'

@app.command("update-trunks")
def update_trunks(
    trunk_id: str = typer.Argument(help="trunkId"),
    name: str = typer.Option(None, "--name", help="A unique name for the dial plan."),
    password: str = typer.Option(None, "--password", help="A password to use on the trunk."),
    dual_identity_support_enabled: bool = typer.Option(None, "--dual-identity-support-enabled/--no-dual-identity-support-enabled", help="Determines the behavior of the From and PAI headers on outbound calls."),
    max_concurrent_calls: str = typer.Option(None, "--max-concurrent-calls", help="Max Concurrent call. Required to create a static certificate-based trunk."),
    p_charge_info_support_policy: str = typer.Option(None, "--p-charge-info-support-policy", help="Choices: DISABLED, ASSERTED_IDENTITY, CONFIGURABLE_CHARGE_NUMBER"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Trunk\n\nExample --json-body:\n  '{"name":"...","password":"...","dualIdentitySupportEnabled":true,"maxConcurrentCalls":0,"pChargeInfoSupportPolicy":"DISABLED"}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_TRUNKS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/{trunk_id}"
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
        if password is not None:
            body["password"] = password
        if dual_identity_support_enabled is not None:
            body["dualIdentitySupportEnabled"] = dual_identity_support_enabled
        if max_concurrent_calls is not None:
            body["maxConcurrentCalls"] = max_concurrent_calls
        if p_charge_info_support_policy is not None:
            body["pChargeInfoSupportPolicy"] = p_charge_info_support_policy
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
        emit({"status": "updated", "id": trunk_id}, output=output, fields=fields)



@app.command("delete-trunks")
def delete_trunks(
    trunk_id: str = typer.Argument(help="trunkId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Trunk."""
    if not force:
        typer.confirm(f"Delete {trunk_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/{trunk_id}"
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
        typer.echo(f"Deleted: {trunk_id}")
    else:
        emit({"status": "deleted", "id": trunk_id}, output=output, fields=fields)



@app.command("list-trunk-types")
def list_trunk_types(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Trunk Types."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/trunkTypes"
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
    items = result.get("trunkTypes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Trunk Type', 'trunkType'), ('Device Types', 'deviceTypes')], limit=limit)



@app.command("list-route-groups")
def list_route_groups(
    name: str = typer.Option(None, "--name", help="Return the list of route groups matching the Route group name.."),
    order: str = typer.Option(None, "--order", help="Order the route groups according to designated fields. Available sort orders are `asc` and `desc`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Routing Groups."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups"
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
    items = result.get("routeGroups", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('In Use', 'inUse')], limit=limit)



_BODY_SKELETON_CREATE_ROUTE_GROUPS = '{"name":"...","localGateways":[{"id":"...","priority":"...","name":"...","locationId":"..."}]}'

@app.command("create-route-groups")
def create_route_groups(
    name: str = typer.Option(None, "--name", help="(required) A unique name for the Route Group."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Route Group for a Organization\n\nExample --json-body:\n  '{"name":"...","localGateways":[{"id":"...","priority":"...","name":"...","locationId":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ROUTE_GROUPS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups"
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



@app.command("show-route-groups")
def show_route_groups(
    route_group_id: str = typer.Argument(help="routeGroupId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read a Route Group for a Organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups/{route_group_id}"
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



_BODY_SKELETON_UPDATE_ROUTE_GROUPS = '{"name":"...","localGateways":[{"id":"...","priority":"...","name":"...","locationId":"..."}]}'

@app.command("update-route-groups")
def update_route_groups(
    route_group_id: str = typer.Argument(help="routeGroupId"),
    name: str = typer.Option(None, "--name", help="A unique name for the Route Group."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Route Group for a Organization\n\nExample --json-body:\n  '{"name":"...","localGateways":[{"id":"...","priority":"...","name":"...","locationId":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ROUTE_GROUPS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups/{route_group_id}"
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
        emit({"status": "updated", "id": route_group_id}, output=output, fields=fields)



@app.command("delete-route-groups")
def delete_route_groups(
    route_group_id: str = typer.Argument(help="routeGroupId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove a Route Group from an Organization."""
    if not force:
        typer.confirm(f"Delete {route_group_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups/{route_group_id}"
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
        typer.echo(f"Deleted: {route_group_id}")
    else:
        emit({"status": "removed", "id": route_group_id}, output=output, fields=fields)



@app.command("show-usage")
def show_usage(
    route_group_id: str = typer.Argument(help="routeGroupId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the Usage of a Routing Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups/{route_group_id}/usage"
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



@app.command("list-usage-call-to-extension-route-groups")
def list_usage_call_to_extension_route_groups(
    route_group_id: str = typer.Argument(help="routeGroupId"),
    location_name: str = typer.Option(None, "--location-name", help="Return the list of locations matching the location name."),
    order: str = typer.Option(None, "--order", help="Order the locations according to designated fields. Available sort orders are `asc`, and `desc`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the Call to Extension Locations of a Routing Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups/{route_group_id}/usageCallToExtension"
    params = {}
    if location_name is not None:
        params["locationName"] = location_name
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
    items = result.get("locations", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-usage-dial-plan")
def list_usage_dial_plan(
    route_group_id: str = typer.Argument(help="routeGroupId"),
    location_name: str = typer.Option(None, "--location-name", help="Return the list of locations matching the location name."),
    order: str = typer.Option(None, "--order", help="Order the locations according to designated fields. Available sort orders are `asc`, and `desc`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the Dial Plan Locations of a Routing Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups/{route_group_id}/usageDialPlan"
    params = {}
    if location_name is not None:
        params["locationName"] = location_name
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
    items = result.get("locations", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-usage-pstn-connection-route-groups")
def list_usage_pstn_connection_route_groups(
    route_group_id: str = typer.Argument(help="routeGroupId"),
    location_name: str = typer.Option(None, "--location-name", help="Return the list of locations matching the location name."),
    order: str = typer.Option(None, "--order", help="Order the locations according to designated fields. Available sort orders are `asc`, and `desc`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the PSTN Connection Locations of a Routing Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups/{route_group_id}/usagePstnConnection"
    params = {}
    if location_name is not None:
        params["locationName"] = location_name
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
    items = result.get("locations", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-usage-route-list")
def list_usage_route_list(
    route_group_id: str = typer.Argument(help="routeGroupId"),
    name: str = typer.Option(None, "--name", help="Return the list of locations matching the location name."),
    order: str = typer.Option(None, "--order", help="Order the locations according to designated fields. Available sort orders are `asc`, and `desc`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the Route Lists of a Routing Group."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeGroups/{route_group_id}/usageRouteList"
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
    items = result.get("routeGroupUsageRouteListGet", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-route-lists")
def list_route_lists(
    order: str = typer.Option(None, "--order", help="Order the Route List according to the designated fields. Available sort fields are `name`, and `locationId`. Sort order is ascending by default"),
    name: str = typer.Option(None, "--name", help="Return the list of Route List matching the route list name."),
    location_id: str = typer.Option(None, "--location-id", help="Return the list of Route Lists matching the location id."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Route Lists."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeLists"
    params = {}
    if order is not None:
        params["order"] = order
    if name is not None:
        params["name"] = name
    if location_id is not None:
        params["locationId"] = location_id
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
    items = result.get("routeLists", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Location', 'locationName')], limit=limit)



_BODY_SKELETON_CREATE_ROUTE_LISTS = '{"name":"...","locationId":"...","routeGroupId":"..."}'

@app.command("create-route-lists")
def create_route_lists(
    name: str = typer.Option(None, "--name", help="(required) Name of the Route List"),
    location_id: str = typer.Option(None, "--location-id", help="(required) Location associated with the Route List."),
    route_group_id: str = typer.Option(None, "--route-group-id", help="(required) ID of the route group associated with Route List."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Route List\n\nExample --json-body:\n  '{"name":"...","locationId":"...","routeGroupId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ROUTE_LISTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeLists"
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
        if location_id is not None:
            body["locationId"] = location_id
        if route_group_id is not None:
            body["routeGroupId"] = route_group_id
        _missing = [f for f in ['name', 'locationId', 'routeGroupId'] if f not in body or body[f] is None]
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



@app.command("show-route-lists")
def show_route_lists(
    route_list_id: str = typer.Argument(help="routeListId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Route List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeLists/{route_list_id}"
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



_BODY_SKELETON_UPDATE_ROUTE_LISTS = '{"name":"...","routeGroupId":"..."}'

@app.command("update-route-lists")
def update_route_lists(
    route_list_id: str = typer.Argument(help="routeListId"),
    name: str = typer.Option(None, "--name", help="Route List new name."),
    route_group_id: str = typer.Option(None, "--route-group-id", help="New route group ID."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a Route List\n\nExample --json-body:\n  '{"name":"...","routeGroupId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ROUTE_LISTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeLists/{route_list_id}"
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
        if route_group_id is not None:
            body["routeGroupId"] = route_group_id
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
        emit({"status": "updated", "id": route_list_id}, output=output, fields=fields)



@app.command("delete-route-lists")
def delete_route_lists(
    route_list_id: str = typer.Argument(help="routeListId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Route List."""
    if not force:
        typer.confirm(f"Delete {route_list_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeLists/{route_list_id}"
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
        typer.echo(f"Deleted: {route_list_id}")
    else:
        emit({"status": "deleted", "id": route_list_id}, output=output, fields=fields)



@app.command("list-numbers")
def list_numbers(
    route_list_id: str = typer.Argument(help="routeListId"),
    number: str = typer.Option(None, "--number", help="Number assigned to the route list."),
    order: str = typer.Option(None, "--order", help="Order the Route Lists according to number, ascending or descending."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Numbers assigned to a Route List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeLists/{route_list_id}/numbers"
    params = {}
    if number is not None:
        params["number"] = number
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
    items = result.get("numbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_UPDATE_NUMBERS = '{"numbers":[{"number":"...","action":"..."}],"deleteAllNumbers":true}'

@app.command("update-numbers")
def update_numbers(
    route_list_id: str = typer.Argument(help="routeListId"),
    delete_all_numbers: bool = typer.Option(None, "--delete-all-numbers/--no-delete-all-numbers", help="If present, the numbers array is ignored and all numbers in the route list are deleted."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Numbers for Route List\n\nExample --json-body:\n  '{"numbers":[{"number":"...","action":"..."}],"deleteAllNumbers":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_NUMBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/routeLists/{route_list_id}/numbers"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if delete_all_numbers is not None:
            body["deleteAllNumbers"] = delete_all_numbers
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
        emit({"status": "updated", "id": route_list_id}, output=output, fields=fields)



@app.command("list-usage-call-to-extension-trunks")
def list_usage_call_to_extension_trunks(
    trunk_id: str = typer.Argument(help="trunkId"),
    order: str = typer.Option(None, "--order", help="Order the trunks according to the designated fields. Available sort fields are `name`, and `locationName`. Sort order is ascending by default"),
    name: str = typer.Option(None, "--name", help="Return the list of trunks matching the local gateway names"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Local Gateway Call to On-Premises Extension Usage for a Trunk."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/premisePstn/trunks/{trunk_id}/usageCallToExtension"
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
    items = result.get("locations", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name')], limit=limit)



@app.command("list-translation-patterns")
def list_translation_patterns(
    limit_to_location_id: str = typer.Option(None, "--limit-to-location-id", help="When a location ID is passed, then return only the corresponding location level translation patterns."),
    limit_to_org_level_enabled: str = typer.Option(None, "--limit-to-org-level-enabled", help="When set to be `true`, then return only the organization-level translation patterns."),
    order: str = typer.Option(None, "--order", help="Sort the list of translation patterns according to translation pattern name, ascending or descending."),
    name: str = typer.Option(None, "--name", help="Only return translation patterns with the matching `name`."),
    matching_pattern: str = typer.Option(None, "--matching-pattern", help="Only return translation patterns with the matching `matchingPattern`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve the list of Translation Patterns."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRouting/translationPatterns"
    params = {}
    if limit_to_location_id is not None:
        params["limitToLocationId"] = limit_to_location_id
    if limit_to_org_level_enabled is not None:
        params["limitToOrgLevelEnabled"] = limit_to_org_level_enabled
    if order is not None:
        params["order"] = order
    if name is not None:
        params["name"] = name
    if matching_pattern is not None:
        params["matchingPattern"] = matching_pattern
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
    items = result.get("translationPatterns", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Pattern', 'matchingPattern'), ('Level', 'level')], limit=limit)



_BODY_SKELETON_CREATE_TRANSLATION_PATTERNS_CALL_ROUTING = '{"name":"...","matchingPattern":"...","replacementPattern":"..."}'

@app.command("create-translation-patterns-call-routing")
def create_translation_patterns_call_routing(
    name: str = typer.Option(None, "--name", help="(required) Name given to a translation pattern for an organization."),
    matching_pattern: str = typer.Option(None, "--matching-pattern", help="(required) Matching pattern given to a translation pattern for an organization."),
    replacement_pattern: str = typer.Option(None, "--replacement-pattern", help="(required) Replacement pattern given to a translation pattern for an organization."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Translation Pattern for an Organization\n\nExample --json-body:\n  '{"name":"...","matchingPattern":"...","replacementPattern":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TRANSLATION_PATTERNS_CALL_ROUTING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRouting/translationPatterns"
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
        if matching_pattern is not None:
            body["matchingPattern"] = matching_pattern
        if replacement_pattern is not None:
            body["replacementPattern"] = replacement_pattern
        _missing = [f for f in ['name', 'matchingPattern', 'replacementPattern'] if f not in body or body[f] is None]
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



@app.command("show-translation-patterns-call-routing")
def show_translation_patterns_call_routing(
    translation_id: str = typer.Argument(help="translationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a specific Translation Pattern for an Organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRouting/translationPatterns/{translation_id}"
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



_BODY_SKELETON_UPDATE_TRANSLATION_PATTERNS_CALL_ROUTING = '{"name":"...","matchingPattern":"...","replacementPattern":"..."}'

@app.command("update-translation-patterns-call-routing")
def update_translation_patterns_call_routing(
    translation_id: str = typer.Argument(help="translationId"),
    name: str = typer.Option(None, "--name", help="Name given to a translation pattern for an organization."),
    matching_pattern: str = typer.Option(None, "--matching-pattern", help="Matching pattern given to a translation pattern for an organization."),
    replacement_pattern: str = typer.Option(None, "--replacement-pattern", help="Replacement pattern given to a translation pattern for an organization."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a specific Translation Pattern for an Organization\n\nExample --json-body:\n  '{"name":"...","matchingPattern":"...","replacementPattern":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_TRANSLATION_PATTERNS_CALL_ROUTING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRouting/translationPatterns/{translation_id}"
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
        if matching_pattern is not None:
            body["matchingPattern"] = matching_pattern
        if replacement_pattern is not None:
            body["replacementPattern"] = replacement_pattern
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
        emit({"status": "updated", "id": translation_id}, output=output, fields=fields)



@app.command("delete-translation-patterns-call-routing")
def delete_translation_patterns_call_routing(
    translation_id: str = typer.Argument(help="translationId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a specific Translation Pattern."""
    if not force:
        typer.confirm(f"Delete {translation_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRouting/translationPatterns/{translation_id}"
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
        typer.echo(f"Deleted: {translation_id}")
    else:
        emit({"status": "deleted", "id": translation_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_TRANSLATION_PATTERNS_CALL_ROUTING_1 = '{"name":"...","matchingPattern":"...","replacementPattern":"..."}'

@app.command("create-translation-patterns-call-routing-1")
def create_translation_patterns_call_routing_1(
    location_id: str = typer.Argument(help="locationId"),
    name: str = typer.Option(None, "--name", help="(required) A name given to a translation pattern for a location."),
    matching_pattern: str = typer.Option(None, "--matching-pattern", help="(required) A matching pattern given to a translation pattern for a location."),
    replacement_pattern: str = typer.Option(None, "--replacement-pattern", help="(required) A replacement pattern given to a translation pattern for a location."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Translation Pattern for a Location\n\nExample --json-body:\n  '{"name":"...","matchingPattern":"...","replacementPattern":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TRANSLATION_PATTERNS_CALL_ROUTING_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRouting/translationPatterns"
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
        if matching_pattern is not None:
            body["matchingPattern"] = matching_pattern
        if replacement_pattern is not None:
            body["replacementPattern"] = replacement_pattern
        _missing = [f for f in ['name', 'matchingPattern', 'replacementPattern'] if f not in body or body[f] is None]
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



@app.command("show-translation-patterns-call-routing-1")
def show_translation_patterns_call_routing_1(
    location_id: str = typer.Argument(help="locationId"),
    translation_id: str = typer.Argument(help="translationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a specific Translation Pattern for a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRouting/translationPatterns/{translation_id}"
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



_BODY_SKELETON_UPDATE_TRANSLATION_PATTERNS_CALL_ROUTING_1 = '{"name":"...","matchingPattern":"...","replacementPattern":"..."}'

@app.command("update-translation-patterns-call-routing-1")
def update_translation_patterns_call_routing_1(
    location_id: str = typer.Argument(help="locationId"),
    translation_id: str = typer.Argument(help="translationId"),
    name: str = typer.Option(None, "--name", help="A name given to a translation pattern for a location."),
    matching_pattern: str = typer.Option(None, "--matching-pattern", help="A matching pattern given to a translation pattern for a location."),
    replacement_pattern: str = typer.Option(None, "--replacement-pattern", help="A replacement pattern given to a translation pattern for a location."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a specific Translation Pattern for a Location\n\nExample --json-body:\n  '{"name":"...","matchingPattern":"...","replacementPattern":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_TRANSLATION_PATTERNS_CALL_ROUTING_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRouting/translationPatterns/{translation_id}"
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
        if matching_pattern is not None:
            body["matchingPattern"] = matching_pattern
        if replacement_pattern is not None:
            body["replacementPattern"] = replacement_pattern
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
        emit({"status": "updated", "id": translation_id}, output=output, fields=fields)



@app.command("delete-translation-patterns-call-routing-1")
def delete_translation_patterns_call_routing_1(
    location_id: str = typer.Argument(help="locationId"),
    translation_id: str = typer.Argument(help="translationId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a specific Translation Pattern for a Location."""
    if not force:
        typer.confirm(f"Delete {translation_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRouting/translationPatterns/{translation_id}"
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
        typer.echo(f"Deleted: {translation_id}")
    else:
        emit({"status": "deleted", "id": translation_id}, output=output, fields=fields)


