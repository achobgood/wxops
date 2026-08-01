import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling emergency-services.")


_BODY_SKELETON_UPDATE = '{"enabled":true,"companyId":"...","secret":"...","externalTenantEnabled":true,"email":"...","password":"..."}'

@app.command("update", short_help="Update RedSky Service Settings.")
def update(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the service is enabled."),
    company_id: str = typer.Option(None, "--company-id", help="The RedSky company ID, which can be retrieved from the RedSky portal."),
    secret: str = typer.Option(None, "--secret", help="The company secret key, which can be found in the RedSky portal."),
    external_tenant_enabled: bool = typer.Option(None, "--external-tenant-enabled/--no-external-tenant-enabled", help="`true` if the RedSky reseller customer is not under a Cisco account."),
    email: str = typer.Option(None, "--email", help="The email for the RedSky account. `email` is required if `externalTenantEnabled` is true."),
    password: str = typer.Option(None, "--password", help="The password for the RedSky account. `password` is required if `externalTenantEnabled` is true."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update RedSky Service Settings.\n\n\b\nExample: wxcli emergency-services update --enabled\n\n\b\nExample --json-body: '{"enabled":true,"companyId":"...","secret":"...","externalTenantEnabled":true,"email":"...","password":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/serviceSettings"
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
        if company_id is not None:
            body["companyId"] = company_id
        if secret is not None:
            body["secret"] = secret
        if external_tenant_enabled is not None:
            body["externalTenantEnabled"] = external_tenant_enabled
        if email is not None:
            body["email"] = email
        if password is not None:
            body["password"] = password
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



@app.command("show", short_help="Retrieve RedSky Account Details for an Organization.")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve RedSky Account Details for an Organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky"
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



_BODY_SKELETON_CREATE = '{"email":"...","orgPrefix":"wxc","partnerRedskyOrgId":"..."}'

@app.command("create", short_help="Create an Account and Admin in RedSky.")
def create(
    org_prefix: str = typer.Option(None, "--org-prefix", help="Choices: wxc, wxc-whs"),
    email: str = typer.Option(None, "--email", help="(required) The email for the RedSky account administrator."),
    partner_redsky_org_id: str = typer.Option(None, "--partner-redsky-org-id", help="New organization is created under this partner organization ID if present, otherwise it will be created under a Cisco partner."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Account and Admin in RedSky.\n\n\b\nExample: wxcli emergency-services create --email EMAIL\n\n\b\nExample --json-body: '{"email":"...","orgPrefix":"wxc","partnerRedskyOrgId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if org_prefix is not None:
            body["orgPrefix"] = org_prefix
        if email is not None:
            body["email"] = email
        if partner_redsky_org_id is not None:
            body["partnerRedskyOrgId"] = partner_redsky_org_id
        _missing = [f for f in ['email'] if f not in body or body[f] is None]
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



@app.command("show-status-red-sky", short_help="Get the Organization Compliance Status for a RedSky Account.")
def show_status_red_sky(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Organization Compliance Status for a RedSky Account."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/status"
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



_BODY_SKELETON_UPDATE_STATUS_RED_SKY = '{"complianceStatus":"OPTED_OUT"}'

@app.command("update-status-red-sky", short_help="Update the Organization RedSky Account's Compliance Status.")
def update_status_red_sky(
    compliance_status: str = typer.Option(None, "--compliance-status", help="Choices: OPTED_OUT, LOCATION_SETUP, ALERTS, NETWORK_ELEMENTS, ROUTING_ENABLED"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Organization RedSky Account's Compliance Status.\n\n\b\nExample: wxcli emergency-services update-status-red-sky --compliance-status OPTED_OUT\n\n\b\nExample --json-body: '{"complianceStatus":"OPTED_OUT"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_STATUS_RED_SKY), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/status"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if compliance_status is not None:
            body["complianceStatus"] = compliance_status
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-compliance-status", short_help="Get the Organization Compliance Status and the Location Status List.")
def show_compliance_status(
    start: str = typer.Option(None, "--start", help="Specifies the offset from the first result that you want to fetch."),
    max: str = typer.Option(None, "--max", help="Specifies the maximum number of records that you want to fetch."),
    order: str = typer.Option(None, "--order", help="Sort the list of locations in ascending or descending order. To sort in descending order append `-desc` to possible sort order values. Possible sort order values are `locationName` and `locationState`."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Organization Compliance Status and the Location Status List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/complianceStatus"
    params = {}
    if start is not None:
        params["start"] = start
    if max is not None:
        params["max"] = max
    if order is not None:
        params["order"] = order
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



_BODY_SKELETON_LOGIN_TO_A = '{"email":"...","password":"...","redSkyOrgId":"..."}'

@app.command("login-to-a", short_help="Login to a RedSky Admin Account.")
def login_to_a(
    email: str = typer.Option(None, "--email", help="Email for the RedSky account."),
    password: str = typer.Option(None, "--password", help="Password for the RedSky account."),
    red_sky_org_id: str = typer.Option(None, "--red-sky-org-id", help="The RedSky organization ID for the organization which can be found in the RedSky portal."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Login to a RedSky Admin Account.\n\n\b\nExample: wxcli emergency-services login-to-a --email EMAIL --password PASSWORD\n\n\b\nExample --json-body: '{"email":"...","password":"...","redSkyOrgId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_LOGIN_TO_A), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/actions/login/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if email is not None:
            body["email"] = email
        if password is not None:
            body["password"] = password
        if red_sky_org_id is not None:
            body["redSkyOrgId"] = red_sky_org_id
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-red-sky", short_help="Get a Location's RedSky Emergency Calling Parameters.")
def show_red_sky(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location's RedSky Emergency Calling Parameters.\n\n\b\nExample: wxcli emergency-services show-red-sky LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky"
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



@app.command("show-status-red-sky-1", short_help="Get a Location's RedSky Compliance Status.")
def show_status_red_sky_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location's RedSky Compliance Status.\n\n\b\nExample: wxcli emergency-services show-status-red-sky-1 LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/status"
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



_BODY_SKELETON_UPDATE_STATUS_RED_SKY_1 = '{"complianceStatus":"OPTED_OUT"}'

@app.command("update-status-red-sky-1", short_help="Update a Location's RedSky Compliance Status.")
def update_status_red_sky_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    compliance_status: str = typer.Option(None, "--compliance-status", help="Choices: OPTED_OUT, LOCATION_SETUP, ALERTS, NETWORK_ELEMENTS, ROUTING_ENABLED"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location's RedSky Compliance Status.\n\n\b\nExample: wxcli emergency-services update-status-red-sky-1 LOCATION_ID --compliance-status OPTED_OUT\n\n\b\nExample --json-body: '{"complianceStatus":"OPTED_OUT"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_STATUS_RED_SKY_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/status"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if compliance_status is not None:
            body["complianceStatus"] = compliance_status
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_BUILDING = '{"alertingEmail":"...","address":{"addressLine1":"...","addressLine2":"...","city":"...","stateOrProvince":"...","zipOrPostalCode":"...","country":"..."}}'

@app.command("create-building", short_help="Create a RedSky Building Address and Alert Email for a Location.")
def create_building(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    alerting_email: str = typer.Option(None, "--alerting-email", help="(required) Email that is used to create alerts in RedSky. At least one email is mandatory."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a RedSky Building Address and Alert Email for a Location.\n\n\b\nExample: wxcli emergency-services create-building LOCATION_ID --alerting-email ALERTING_EMAIL\n\n\b\nExample --json-body: '{"alertingEmail":"...","address":{"addressLine1":"...","addressLine2":"...","city":"...","stateOrProvince":"...","zipOrPostalCode":"...","country":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BUILDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/building"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if alerting_email is not None:
            body["alertingEmail"] = alerting_email
        _missing = [f for f in ['alertingEmail'] if f not in body or body[f] is None]
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



_BODY_SKELETON_UPDATE_BUILDING = '{"address":{"addressLine1":"...","addressLine2":"...","city":"...","stateOrProvince":"...","zipOrPostalCode":"...","country":"..."}}'

@app.command("update-building", short_help="Update a RedSky Building Address for a Location.")
def update_building(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a RedSky Building Address for a Location.\n\n\b\nExample: wxcli emergency-services update-building LOCATION_ID\n\n\b\nExample --json-body: '{"address":{"addressLine1":"...","addressLine2":"...","city":"...","stateOrProvince":"...","zipOrPostalCode":"...","country":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_BUILDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/building"
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
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("show-emergency-call-notification-config", short_help="Get an Organization Emergency Call Notification.")
def show_emergency_call_notification_config(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get an Organization Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/emergencyCallNotification"
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



_BODY_SKELETON_UPDATE_EMERGENCY_CALL_NOTIFICATION_CONFIG = '{"emergencyCallNotificationEnabled":true,"allowEmailNotificationAllLocationEnabled":true,"emailAddress":"..."}'

@app.command("update-emergency-call-notification-config", short_help="Update an Organization Emergency Call Notification.")
def update_emergency_call_notification_config(
    emergency_call_notification_enabled: bool = typer.Option(None, "--emergency-call-notification-enabled/--no-emergency-call-notification-enabled", help="When true sends an email to the specified email address when a call is made to emergency services."),
    allow_email_notification_all_location_enabled: bool = typer.Option(None, "--allow-email-notification-all-location-enabled/--no-allow-email-notification-all-location-enabled", help="Send an emergency call notification email for all locations."),
    email_address: str = typer.Option(None, "--email-address", help="When `emergencyCallNotificationEnabled` is true, the emergency notification email is sent to the specified email address."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Organization Emergency Call Notification.\n\n\b\nExample --json-body: '{"emergencyCallNotificationEnabled":true,"allowEmailNotificationAllLocationEnabled":true,"emailAddress":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EMERGENCY_CALL_NOTIFICATION_CONFIG), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/emergencyCallNotification"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if emergency_call_notification_enabled is not None:
            body["emergencyCallNotificationEnabled"] = emergency_call_notification_enabled
        if allow_email_notification_all_location_enabled is not None:
            body["allowEmailNotificationAllLocationEnabled"] = allow_email_notification_all_location_enabled
        if email_address is not None:
            body["emailAddress"] = email_address
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-emergency-call-notification-locations", short_help="Get a Location Emergency Call Notification.")
def show_emergency_call_notification_locations(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location Emergency Call Notification.\n\n\b\nExample: wxcli emergency-services show-emergency-call-notification-locations LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/emergencyCallNotification"
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



_BODY_SKELETON_UPDATE_EMERGENCY_CALL_NOTIFICATION_LOCATIONS = '{"emergencyCallNotificationEnabled":true,"emailAddress":"..."}'

@app.command("update-emergency-call-notification-locations", short_help="Update a Location Emergency Call Notification.")
def update_emergency_call_notification_locations(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    emergency_call_notification_enabled: bool = typer.Option(None, "--emergency-call-notification-enabled/--no-emergency-call-notification-enabled", help="When true sends an email to the specified email address when a call is made from this location to emergency services."),
    email_address: str = typer.Option(None, "--email-address", help="Sends an email to this email address when a call is made from this location to emergency services and `emergencyCallNotificationEnabled` is true."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location Emergency Call Notification.\n\n\b\nExample: wxcli emergency-services update-emergency-call-notification-locations LOCATION_ID\n\n\b\nExample --json-body: '{"emergencyCallNotificationEnabled":true,"emailAddress":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EMERGENCY_CALL_NOTIFICATION_LOCATIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/emergencyCallNotification"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if emergency_call_notification_enabled is not None:
            body["emergencyCallNotificationEnabled"] = emergency_call_notification_enabled
        if email_address is not None:
            body["emailAddress"] = email_address
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("show-dependencies-emergency-callback-number", short_help="Get Dependencies for a Hunt Group Emergency Callback Number.")
def show_dependencies_emergency_callback_number(
    hunt_group_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli hunt-group list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Dependencies for a Hunt Group Emergency Callback Number.\n\n\b\nExample: wxcli emergency-services show-dependencies-emergency-callback-number HUNT_GROUP_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/huntGroups/{hunt_group_id}/emergencyCallbackNumber/dependencies"
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



@app.command("show-emergency-callback-number-people", short_help="Get a Person's Emergency Callback Number.")
def show_emergency_callback_number_people(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Person's Emergency Callback Number.\n\n\b\nExample: wxcli emergency-services show-emergency-callback-number-people PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber"
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



_BODY_SKELETON_UPDATE_EMERGENCY_CALLBACK_NUMBER_PEOPLE = '{"selected":"DIRECT_LINE","locationMemberId":"...","elinEnabled":true,"elinForWebexAppEnabled":true}'

@app.command("update-emergency-callback-number-people", short_help="Update a Person's Emergency Callback Number.")
def update_emergency_callback_number_people(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    selected: str = typer.Option(None, "--selected", help="Choices: DIRECT_LINE, LOCATION_ECBN, LOCATION_MEMBER_NUMBER"),
    location_member_id: str = typer.Option(None, "--location-member-id", help="Member ID of person/workspace/virtual line/hunt group within the location. Required when `selected` is `LOCATION_MEMBER_NUMBER`."),
    elin_enabled: bool = typer.Option(None, "--elin-enabled/--no-elin-enabled", help="Indicates whether this person is allowed to use an Emergency Location Identification Number (ELIN) for emergency calls made from one of their devices."),
    elin_for_webex_app_enabled: bool = typer.Option(None, "--elin-for-webex-app-enabled/--no-elin-for-webex-app-enabled", help="Indicates whether this member is allowed to use an Emergency Location Identification Number (ELIN) for emergency calls made using Webex App."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Person's Emergency Callback Number.\n\n\b\nExample: wxcli emergency-services update-emergency-callback-number-people PERSON_ID\n\n\b\nExample --json-body: '{"selected":"DIRECT_LINE","locationMemberId":"...","elinEnabled":true,"elinForWebexAppEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EMERGENCY_CALLBACK_NUMBER_PEOPLE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
        if elin_enabled is not None:
            body["elinEnabled"] = elin_enabled
        if elin_for_webex_app_enabled is not None:
            body["elinForWebexAppEnabled"] = elin_for_webex_app_enabled
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
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("show-dependencies-emergency-callback-number-1", short_help="Retrieve A Person's Emergency Callback Number Dependencies.")
def show_dependencies_emergency_callback_number_1(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli people list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve A Person's Emergency Callback Number Dependencies.\n\n\b\nExample: wxcli emergency-services show-dependencies-emergency-callback-number-1 PERSON_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber/dependencies"
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



@app.command("show-emergency-callback-number-workspaces", short_help="Get a Workspace Emergency Callback Number.")
def show_emergency_callback_number_workspaces(
    workspace_id: str = typer.Argument(help="Webex PLACE id, from: wxcli workspaces list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Workspace Emergency Callback Number.\n\n\b\nExample: wxcli emergency-services show-emergency-callback-number-workspaces WORKSPACE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber"
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



_BODY_SKELETON_UPDATE_EMERGENCY_CALLBACK_NUMBER_WORKSPACES = '{"selected":"DIRECT_LINE","locationMemberId":"...","elinEnabled":true}'

@app.command("update-emergency-callback-number-workspaces", short_help="Update a Workspace Emergency Callback Number.")
def update_emergency_callback_number_workspaces(
    workspace_id: str = typer.Argument(help="Webex PLACE id, from: wxcli workspaces list"),
    selected: str = typer.Option(None, "--selected", help="Choices: DIRECT_LINE, LOCATION_ECBN, LOCATION_MEMBER_NUMBER"),
    location_member_id: str = typer.Option(None, "--location-member-id", help="Member ID of person/workspace/virtual line/hunt group within the location. Required when `selected` is `LOCATION_MEMBER_NUMBER`."),
    elin_enabled: bool = typer.Option(None, "--elin-enabled/--no-elin-enabled", help="Indicates whether this workspace is allowed to use an Emergency Location Identification Number (ELIN) for emergency calls made from one of its devices."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Workspace Emergency Callback Number.\n\n\b\nExample: wxcli emergency-services update-emergency-callback-number-workspaces WORKSPACE_ID\n\n\b\nExample --json-body: '{"selected":"DIRECT_LINE","locationMemberId":"...","elinEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EMERGENCY_CALLBACK_NUMBER_WORKSPACES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
        if elin_enabled is not None:
            body["elinEnabled"] = elin_enabled
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
        emit({"status": "updated", "id": workspace_id}, output=output, fields=fields)



@app.command("show-dependencies-emergency-callback-number-2", short_help="Retrieve Workspace Emergency Callback Number Dependencies.")
def show_dependencies_emergency_callback_number_2(
    workspace_id: str = typer.Argument(help="Webex PLACE id, from: wxcli workspaces list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Workspace Emergency Callback Number Dependencies.\n\n\b\nExample: wxcli emergency-services show-dependencies-emergency-callback-number-2 WORKSPACE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber/dependencies"
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



@app.command("show-dependencies-emergency-callback-number-3", short_help="Get Dependencies for a Virtual Line Emergency Callback Number.")
def show_dependencies_emergency_callback_number_3(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_PROFILE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Dependencies for a Virtual Line Emergency Callback Number.\n\n\b\nExample: wxcli emergency-services show-dependencies-emergency-callback-number-3 VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber/dependencies"
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



@app.command("show-emergency-callback-number-virtual-lines", short_help="Get the Virtual Line's Emergency Callback Settings.")
def show_emergency_callback_number_virtual_lines(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Virtual Line's Emergency Callback Settings.\n\n\b\nExample: wxcli emergency-services show-emergency-callback-number-virtual-lines VIRTUAL_LINE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber"
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



_BODY_SKELETON_UPDATE_EMERGENCY_CALLBACK_NUMBER_VIRTUAL_LINES = '{"selected":"DIRECT_LINE","locationMemberId":"..."}'

@app.command("update-emergency-callback-number-virtual-lines", short_help="Update a Virtual Line's Emergency Callback settings.")
def update_emergency_callback_number_virtual_lines(
    virtual_line_id: str = typer.Argument(help="Webex VIRTUAL_LINE id, from: wxcli virtual-line-settings list"),
    selected: str = typer.Option(None, "--selected", help="Choices: DIRECT_LINE, LOCATION_ECBN, LOCATION_MEMBER_NUMBER"),
    location_member_id: str = typer.Option(None, "--location-member-id", help="Member ID of person/workspace/virtual line/hunt group within the location. Required when `selected` is `LOCATION_MEMBER_NUMBER`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Virtual Line's Emergency Callback settings.\n\n\b\nExample: wxcli emergency-services update-emergency-callback-number-virtual-lines VIRTUAL_LINE_ID --selected DIRECT_LINE\n\n\b\nExample --json-body: '{"selected":"DIRECT_LINE","locationMemberId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_EMERGENCY_CALLBACK_NUMBER_VIRTUAL_LINES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
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
        emit({"status": "updated", "id": virtual_line_id}, output=output, fields=fields)


