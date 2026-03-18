import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling emergency-services-settings.")


@app.command("update")
def update(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    company_id: str = typer.Option(None, "--company-id", help=""),
    secret: str = typer.Option(None, "--secret", help=""),
    external_tenant_enabled: bool = typer.Option(None, "--external-tenant-enabled/--no-external-tenant-enabled", help=""),
    email: str = typer.Option(None, "--email", help=""),
    password: str = typer.Option(None, "--password", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update RedSky Service Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/serviceSettings"
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create")
def create(
    email: str = typer.Option(None, "--email", help=""),
    org_prefix: str = typer.Option(None, "--org-prefix", help=""),
    partner_redsky_org_id: str = typer.Option(None, "--partner-redsky-org-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Account and Admin in RedSky."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if email is not None:
            body["email"] = email
        if org_prefix is not None:
            body["orgPrefix"] = org_prefix
        if partner_redsky_org_id is not None:
            body["partnerRedskyOrgId"] = partner_redsky_org_id
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve RedSky Account Details for an Organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-status-red-sky")
def update_status_red_sky(
    compliance_status: str = typer.Option(None, "--compliance-status", help="e.g. ROUTING_ENABLED"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Organization RedSky Account's Compliance Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/status"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if compliance_status is not None:
            body["complianceStatus"] = compliance_status
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Organization Compliance Status for a RedSky Account."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/status"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("show-compliance-status")
def show_compliance_status(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Organization Compliance Status and the Location Status List."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/complianceStatus"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("login-to-a")
def login_to_a(
    email: str = typer.Option(None, "--email", help=""),
    password: str = typer.Option(None, "--password", help=""),
    red_sky_org_id: str = typer.Option(None, "--red-sky-org-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Login to a RedSky Admin Account."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/actions/login/invoke"
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
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("list-status")
def list_status(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location's RedSky Compliance Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/status"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-status-red-sky-1")
def update_status_red_sky_1(
    location_id: str = typer.Argument(help="locationId"),
    compliance_status: str = typer.Option(None, "--compliance-status", help="e.g. ROUTING_ENABLED"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location's RedSky Compliance Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/status"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if compliance_status is not None:
            body["complianceStatus"] = compliance_status
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create-building")
def create_building(
    location_id: str = typer.Argument(help="locationId"),
    alerting_email: str = typer.Option(None, "--alerting-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a RedSky Building Address and Alert Email for a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/building"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if alerting_email is not None:
            body["alertingEmail"] = alerting_email
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("update-building")
def update_building(
    location_id: str = typer.Argument(help="locationId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a RedSky Building Address for a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/building"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-emergency-call-notification-config")
def show_emergency_call_notification_config(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get an Organization Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/emergencyCallNotification"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-emergency-call-notification-config")
def update_emergency_call_notification_config(
    emergency_call_notification_enabled: bool = typer.Option(None, "--emergency-call-notification-enabled/--no-emergency-call-notification-enabled", help=""),
    allow_email_notification_all_location_enabled: bool = typer.Option(None, "--allow-email-notification-all-location-enabled/--no-allow-email-notification-all-location-enabled", help=""),
    email_address: str = typer.Option(None, "--email-address", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Organization Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/emergencyCallNotification"
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
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-emergency-call-notification-locations")
def update_emergency_call_notification_locations(
    location_id: str = typer.Argument(help="locationId"),
    emergency_call_notification_enabled: bool = typer.Option(None, "--emergency-call-notification-enabled/--no-emergency-call-notification-enabled", help=""),
    email_address: str = typer.Option(None, "--email-address", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Location Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/emergencyCallNotification"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if emergency_call_notification_enabled is not None:
            body["emergencyCallNotificationEnabled"] = emergency_call_notification_enabled
        if email_address is not None:
            body["emailAddress"] = email_address
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-dependencies-emergency-callback-number")
def list_dependencies_emergency_callback_number(
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Dependencies for a Hunt Group Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/huntGroups/{hunt_group_id}/emergencyCallbackNumber/dependencies"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("dependencies", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-emergency-callback-number-people")
def show_emergency_callback_number_people(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Person's Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-emergency-callback-number-people")
def update_emergency_callback_number_people(
    person_id: str = typer.Argument(help="personId"),
    selected: str = typer.Option(None, "--selected", help="e.g. DIRECT_LINE"),
    location_member_id: str = typer.Option(None, "--location-member-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Person's Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-dependencies-emergency-callback-number-1")
def list_dependencies_emergency_callback_number_1(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve A Person's Emergency Callback Number Dependencies."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber/dependencies"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("dependencies", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-emergency-callback-number-workspaces")
def show_emergency_callback_number_workspaces(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Workspace Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-emergency-callback-number-workspaces")
def update_emergency_callback_number_workspaces(
    workspace_id: str = typer.Argument(help="workspaceId"),
    selected: str = typer.Option(None, "--selected", help="e.g. DIRECT_LINE"),
    location_member_id: str = typer.Option(None, "--location-member-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Workspace Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-dependencies-emergency-callback-number-2")
def list_dependencies_emergency_callback_number_2(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Workspace Emergency Callback Number Dependencies."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber/dependencies"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("dependencies", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-dependencies-emergency-callback-number-3")
def list_dependencies_emergency_callback_number_3(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Dependencies for a Virtual Line Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber/dependencies"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("dependencies", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-emergency-callback-number-virtual-lines")
def show_emergency_callback_number_virtual_lines(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Virtual Line's Emergency Callback settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-emergency-callback-number-virtual-lines")
def update_emergency_callback_number_virtual_lines(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    selected: str = typer.Option(None, "--selected", help="e.g. DIRECT_LINE"),
    location_member_id: str = typer.Option(None, "--location-member-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Virtual Line's Emergency Callback settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/virtualLines/{virtual_line_id}/emergencyCallbackNumber"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if selected is not None:
            body["selected"] = selected
        if location_member_id is not None:
            body["locationMemberId"] = location_member_id
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")


