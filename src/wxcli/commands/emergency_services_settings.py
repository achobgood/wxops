import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.errors import handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling emergency-services-settings.")


@app.command("update")
def update(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="`true` if the service is enabled."),
    company_id: str = typer.Option(None, "--company-id", help="The RedSky company ID, which can be retrieved from the RedSk"),
    secret: str = typer.Option(None, "--secret", help="The company secret key, which can be found in the RedSky por"),
    external_tenant_enabled: bool = typer.Option(None, "--external-tenant-enabled/--no-external-tenant-enabled", help="`true` if the RedSky reseller customer is not under a Cisco"),
    email: str = typer.Option(None, "--email", help="The email for the RedSky account. `email` is required if `ex"),
    password: str = typer.Option(None, "--password", help="The password for the RedSky account. `password` is required"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update RedSky Service Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/serviceSettings"
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
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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



@app.command("create")
def create(
    org_prefix: str = typer.Option(None, "--org-prefix", help="Choices: wxc, wxc-whs"),
    email: str = typer.Option(None, "--email", help="(required) The email for the RedSky account administrator."),
    partner_redsky_org_id: str = typer.Option(None, "--partner-redsky-org-id", help="New organization is created under this partner organization"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Account and Admin in RedSky\n\nExample --json-body:\n  '{"orgPrefix":"wxc","email":"...","partnerRedskyOrgId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-status-red-sky")
def show_status_red_sky(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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



@app.command("update-status-red-sky")
def update_status_red_sky(
    compliance_status: str = typer.Option(None, "--compliance-status", help="Choices: OPTED_OUT, LOCATION_SETUP, ALERTS, NETWORK_ELEMENTS, ROUTING_ENABLED"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Organization RedSky Account's Compliance Status\n\nExample --json-body:\n  '{"complianceStatus":"OPTED_OUT"}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/status"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if compliance_status is not None:
            body["complianceStatus"] = compliance_status
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-compliance-status")
def show_compliance_status(
    start: str = typer.Option(None, "--start", help="Specifies the offset from the first result that you want to"),
    max: str = typer.Option(None, "--max", help="Specifies the maximum number of records that you want to fet"),
    order: str = typer.Option(None, "--order", help="Sort the list of locations in ascending or descending order."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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



@app.command("login-to-a")
def login_to_a(
    email: str = typer.Option(None, "--email", help="Email for the RedSky account."),
    password: str = typer.Option(None, "--password", help="Password for the RedSky account."),
    red_sky_org_id: str = typer.Option(None, "--red-sky-org-id", help="The RedSky organization ID for the organization which can be"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Login to a RedSky Admin Account."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/actions/login/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        handle_rest_error(e)
    print_json(result)



@app.command("show-red-sky")
def show_red_sky(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location's RedSky Emergency Calling Parameters."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("show-status-red-sky-1")
def show_status_red_sky_1(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location's RedSky Compliance Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/status"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("update-status-red-sky-1")
def update_status_red_sky_1(
    location_id: str = typer.Argument(help="locationId"),
    compliance_status: str = typer.Option(None, "--compliance-status", help="Choices: OPTED_OUT, LOCATION_SETUP, ALERTS, NETWORK_ELEMENTS, ROUTING_ENABLED"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location's RedSky Compliance Status\n\nExample --json-body:\n  '{"complianceStatus":"OPTED_OUT"}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/status"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if compliance_status is not None:
            body["complianceStatus"] = compliance_status
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("create-building")
def create_building(
    location_id: str = typer.Argument(help="locationId"),
    alerting_email: str = typer.Option(None, "--alerting-email", help="(required) Email that is used to create alerts in RedSky. At least one"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a RedSky Building Address and Alert Email for a Location\n\nExample --json-body:\n  '{"alertingEmail":"...","address":{"addressLine1":"...","addressLine2":"...","city":"...","stateOrProvince":"...","zipOrPostalCode":"...","country":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/building"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("update-building")
def update_building(
    location_id: str = typer.Argument(help="locationId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a RedSky Building Address for a Location\n\nExample --json-body:\n  '{"address":{"addressLine1":"...","addressLine2":"...","city":"...","stateOrProvince":"...","zipOrPostalCode":"...","country":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/building"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-emergency-call-notification-config")
def show_emergency_call_notification_config(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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



@app.command("update-emergency-call-notification-config")
def update_emergency_call_notification_config(
    emergency_call_notification_enabled: bool = typer.Option(None, "--emergency-call-notification-enabled/--no-emergency-call-notification-enabled", help="When true sends an email to the specified email address when"),
    allow_email_notification_all_location_enabled: bool = typer.Option(None, "--allow-email-notification-all-location-enabled/--no-allow-email-notification-all-location-enabled", help="Send an emergency call notification email for all locations."),
    email_address: str = typer.Option(None, "--email-address", help="When `emergencyCallNotificationEnabled` is true, the emergen"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Organization Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/emergencyCallNotification"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-emergency-call-notification-locations")
def show_emergency_call_notification_locations(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/emergencyCallNotification"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("update-emergency-call-notification-locations")
def update_emergency_call_notification_locations(
    location_id: str = typer.Argument(help="locationId"),
    emergency_call_notification_enabled: bool = typer.Option(None, "--emergency-call-notification-enabled/--no-emergency-call-notification-enabled", help="When true sends an email to the specified email address when"),
    email_address: str = typer.Option(None, "--email-address", help="Sends an email to this email address when a call is made fro"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/emergencyCallNotification"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if emergency_call_notification_enabled is not None:
            body["emergencyCallNotificationEnabled"] = emergency_call_notification_enabled
        if email_address is not None:
            body["emailAddress"] = email_address
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-dependencies-emergency-callback-number")
def show_dependencies_emergency_callback_number(
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Dependencies for a Hunt Group Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/huntGroups/{hunt_group_id}/emergencyCallbackNumber/dependencies"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("show-emergency-callback-number-people")
def show_emergency_callback_number_people(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Person's Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("update-emergency-callback-number-people")
def update_emergency_callback_number_people(
    person_id: str = typer.Argument(help="personId"),
    selected: str = typer.Option(None, "--selected", help="Choices: DIRECT_LINE, LOCATION_ECBN, LOCATION_MEMBER_NUMBER"),
    location_member_id: str = typer.Option(None, "--location-member-id", help="Member ID of person/workspace/virtual line/hunt group within"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Person's Emergency Callback Number\n\nExample --json-body:\n  '{"selected":"DIRECT_LINE","locationMemberId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-dependencies-emergency-callback-number-1")
def show_dependencies_emergency_callback_number_1(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve A Person's Emergency Callback Number Dependencies."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber/dependencies"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("show-emergency-callback-number-workspaces")
def show_emergency_callback_number_workspaces(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Workspace Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("update-emergency-callback-number-workspaces")
def update_emergency_callback_number_workspaces(
    workspace_id: str = typer.Argument(help="workspaceId"),
    selected: str = typer.Option(None, "--selected", help="Choices: DIRECT_LINE, LOCATION_ECBN, LOCATION_MEMBER_NUMBER"),
    location_member_id: str = typer.Option(None, "--location-member-id", help="Member ID of person/workspace/virtual line/hunt group within"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Workspace Emergency Callback Number\n\nExample --json-body:\n  '{"selected":"DIRECT_LINE","locationMemberId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-dependencies-emergency-callback-number-2")
def show_dependencies_emergency_callback_number_2(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Workspace Emergency Callback Number Dependencies."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber/dependencies"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("show-dependencies-emergency-callback-number-3")
def show_dependencies_emergency_callback_number_3(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Dependencies for a Virtual Line Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber/dependencies"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("show-emergency-callback-number-virtual-lines")
def show_emergency_callback_number_virtual_lines(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Virtual Line's Emergency Callback settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("update-emergency-callback-number-virtual-lines")
def update_emergency_callback_number_virtual_lines(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    selected: str = typer.Option(None, "--selected", help="Choices: DIRECT_LINE, LOCATION_ECBN, LOCATION_MEMBER_NUMBER"),
    location_member_id: str = typer.Option(None, "--location-member-id", help="Member ID of person/workspace/virtual line/hunt group within"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Virtual Line's Emergency Callback settings\n\nExample --json-body:\n  '{"selected":"DIRECT_LINE","locationMemberId":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")


