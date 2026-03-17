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



@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve RedSky Account Details for an Organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky"
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
    items = result.get("redSky", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-status")
def update_status(
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



@app.command("list-status")
def list_status(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Organization Compliance Status for a RedSky Account."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/redSky/status"
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
    items = result.get("status", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-compliance-status")
def list_compliance_status(
    start: str = typer.Option(None, "--start", help="Specifies the offset from the first result that you want to"),
    max: str = typer.Option(None, "--max", help="Specifies the maximum number of records that you want to fet"),
    order: str = typer.Option(None, "--order", help="Sort the list of locations in ascending or descending order."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    items = result.get("complianceStatus", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



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



@app.command("list-red-sky")
def list_red_sky(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location's RedSky Emergency Calling Parameters."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky"
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
    items = result.get("redSky", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-status")
def list_status(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location's RedSky Compliance Status."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/redSky/status"
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
    items = result.get("status", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-status")
def update_status(
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



@app.command("list-emergency-call-notification")
def list_emergency_call_notification(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get an Organization Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/emergencyCallNotification"
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
    items = result.get("emergencyCallNotification", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-emergency-call-notification")
def update_emergency_call_notification(
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



@app.command("list-emergency-call-notification")
def list_emergency_call_notification(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Location Emergency Call Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/emergencyCallNotification"
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
    items = result.get("emergencyCallNotification", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-emergency-call-notification")
def update_emergency_call_notification(
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



@app.command("list-dependencies")
def list_dependencies(
    hunt_group_id: str = typer.Argument(help="huntGroupId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
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



@app.command("list-emergency-callback-number")
def list_emergency_callback_number(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Person's Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/emergencyCallbackNumber"
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
    items = result.get("emergencyCallbackNumber", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-emergency-callback-number")
def update_emergency_callback_number(
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



@app.command("list-dependencies")
def list_dependencies(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
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



@app.command("list-emergency-callback-number")
def list_emergency_callback_number(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Workspace Emergency Callback Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/workspaces/{workspace_id}/emergencyCallbackNumber"
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
    items = result.get("emergencyCallbackNumber", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-emergency-callback-number")
def update_emergency_callback_number(
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



@app.command("list-dependencies")
def list_dependencies(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
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



@app.command("list-dependencies")
def list_dependencies(
    virtual_line_id: str = typer.Argument(help="virtualLineId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
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



@app.command("show")
def show(
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



@app.command("update-emergency-callback-number")
def update_emergency_callback_number(
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


