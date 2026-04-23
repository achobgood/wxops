import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling wholesale-provisioning.")


@app.command("list")
def cmd_list(
    external_id: str = typer.Option(None, "--external-id", help="Customer external ID."),
    status: str = typer.Option(None, "--status", help="Customer API status."),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Wholesale Customers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers"
    params = {}
    if external_id is not None:
        params["externalId"] = external_id
    if status is not None:
        params["status"] = status
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["offset"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="(required) This Provisioning ID defines how this customer is to be prov"),
    org_id: str = typer.Option(None, "--org-id", help="The organization ID of the enterprise in Webex. Mandatory fo"),
    external_id: str = typer.Option(None, "--external-id", help="(required) External ID of the Wholesale customer."),
    sub_partner_admin_email: str = typer.Option(None, "--sub-partner-admin-email", help="The email of the sub partner organization admin."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Provision a Wholesale Customer\n\nExample --json-body:\n  '{"provisioningId":"...","packages":["common_area_calling"],"externalId":"...","address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"orgId":"...","customerInfo":{"name":"...","primaryEmail":"...","language":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}},"subPartnerAdminEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if provisioning_id is not None:
            body["provisioningId"] = provisioning_id
        if org_id is not None:
            body["orgId"] = org_id
        if external_id is not None:
            body["externalId"] = external_id
        if sub_partner_admin_email is not None:
            body["subPartnerAdminEmail"] = sub_partner_admin_email
        _missing = [f for f in ['provisioningId', 'externalId'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show")
def show(
    customer_id: str = typer.Argument(help="customerId"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    include_package_license_info: str = typer.Option(None, "--include-package-license-info", help="If specified as true, a list of licenseIds will be returned"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Wholesale Customer."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers/{customer_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if include_package_license_info is not None:
        params["includePackageLicenseInfo"] = include_package_license_info
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    customer_id: str = typer.Argument(help="customerId"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    external_id: str = typer.Option(None, "--external-id", help="External ID of the Wholesale customer."),
    sub_partner_admin_email: str = typer.Option(None, "--sub-partner-admin-email", help="The email of the sub partner organization admin."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Wholesale Customer\n\nExample --json-body:\n  '{"packages":["common_area_calling"],"externalId":"...","address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}},"subPartnerAdminEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers/{customer_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if external_id is not None:
            body["externalId"] = external_id
        if sub_partner_admin_email is not None:
            body["subPartnerAdminEmail"] = sub_partner_admin_email
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    customer_id: str = typer.Argument(help="customerId"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove a Wholesale Customer."""
    if not force:
        typer.confirm(f"Delete {customer_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers/{customer_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    try:
        api.session.rest_delete(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {customer_id}")



@app.command("create-validate-customers")
def create_validate_customers(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="Defines how this wholesale customer is to be provisioned for"),
    org_id: str = typer.Option(None, "--org-id", help="The organization ID of the enterprise in Cisco Webex."),
    external_id: str = typer.Option(None, "--external-id", help="External ID of the Wholesale customer."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Precheck a Wholesale Customer Provisioning\n\nExample --json-body:\n  '{"address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"provisioningId":"...","packages":["common_area_calling"],"orgId":"...","externalId":"...","customerInfo":{"primaryEmail":"...","name":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers/validate"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if provisioning_id is not None:
            body["provisioningId"] = provisioning_id
        if org_id is not None:
            body["orgId"] = org_id
        if external_id is not None:
            body["externalId"] = external_id
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-sub-partners")
def list_sub_partners(
    provisioning_state: str = typer.Option(None, "--provisioning-state", help="Status to filter sub-partners based on provisioning state."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Wholesale Sub-partners."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subPartners"
    params = {}
    if provisioning_state is not None:
        params["provisioningState"] = provisioning_state
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["offset"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-subscribers")
def list_subscribers(
    customer_id: str = typer.Option(None, "--customer-id", help="Wholesale customer ID."),
    person_id: str = typer.Option(None, "--person-id", help="The person ID of the subscriber used in the [/v1/people API]"),
    external_customer_id: str = typer.Option(None, "--external-customer-id", help="Customer external ID."),
    email: str = typer.Option(None, "--email", help="The email address of the subscriber."),
    status: str = typer.Option(None, "--status", help="The provisioning status of the subscriber."),
    after: str = typer.Option(None, "--after", help="Only include subscribers created after this date and time. E"),
    last_status_change: str = typer.Option(None, "--last-status-change", help="Only include subscribers with a provisioning status change a"),
    sort_by: str = typer.Option(None, "--sort-by", help="Supported `sortBy` attributes are `created` and `lastStatusC"),
    sort_order: str = typer.Option(None, "--sort-order", help="Sort by `ASC` (ascending) or `DESC` (descending)."),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Wholesale Subscribers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers"
    params = {}
    if customer_id is not None:
        params["customerId"] = customer_id
    if person_id is not None:
        params["personId"] = person_id
    if external_customer_id is not None:
        params["externalCustomerId"] = external_customer_id
    if email is not None:
        params["email"] = email
    if status is not None:
        params["status"] = status
    if after is not None:
        params["after"] = after
    if last_status_change is not None:
        params["lastStatusChange"] = last_status_change
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_order is not None:
        params["sortOrder"] = sort_order
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["offset"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-subscribers")
def create_subscribers(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    customer_id: str = typer.Option(None, "--customer-id", help="(required) ID of the Provisioned Customer for Webex Wholesale."),
    email: str = typer.Option(None, "--email", help="(required) The email address of the subscriber (mandatory for the trust"),
    package: str = typer.Option(None, "--package", help="Choices: webex_calling, webex_meetings, webex_suite, webex_voice, cx_essentials, webex_calling_standard"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Provision a Wholesale Subscriber\n\nExample --json-body:\n  '{"customerId":"...","email":"...","provisioningParameters":{"firstName":"...","lastName":"...","primaryPhoneNumber":"...","extension":"...","locationId":"..."},"package":"webex_calling","packages":["webex_calling"]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if customer_id is not None:
            body["customerId"] = customer_id
        if email is not None:
            body["email"] = email
        if package is not None:
            body["package"] = package
        _missing = [f for f in ['customerId', 'email'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-subscribers")
def show_subscribers(
    subscriber_id: str = typer.Argument(help="subscriberId"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Wholesale Subscriber."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers/{subscriber_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-subscribers")
def update_subscribers(
    subscriber_id: str = typer.Argument(help="subscriberId"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    package: str = typer.Option(None, "--package", help="The Webex Wholesale package to be assigned to the subscriber (use --help for choices)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Wholesale Subscriber\n\nExample --json-body:\n  '{"package":"webex_calling","packages":["webex_calling"],"provisioningParameters":{"primaryPhoneNumber":"...","extension":"...","locationId":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers/{subscriber_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if package is not None:
            body["package"] = package
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete-subscribers")
def delete_subscribers(
    subscriber_id: str = typer.Argument(help="subscriberId"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove a Wholesale Subscriber."""
    if not force:
        typer.confirm(f"Delete {subscriber_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers/{subscriber_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    try:
        api.session.rest_delete(url, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {subscriber_id}")



@app.command("create-validate-subscribers")
def create_validate_subscribers(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="Defines how this wholesale subscriber is to be provisioned f"),
    customer_id: str = typer.Option(None, "--customer-id", help="ID of the Provisioned Customer for Webex Wholesale."),
    email: str = typer.Option(None, "--email", help="(required) The email address of the subscriber."),
    package: str = typer.Option(None, "--package", help="Choices: webex_calling, webex_meetings, webex_suite, webex_voice, cx_essentials, webex_calling_standard"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Precheck a Wholesale Subscriber Provisioning\n\nExample --json-body:\n  '{"email":"...","provisioningId":"...","customerId":"...","package":"webex_calling","packages":["webex_calling"],"provisioningParameters":{"firstName":"...","lastName":"...","primaryPhoneNumber":"...","extension":"...","locationId":"..."},"customerInfo":{"primaryEmail":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers/validate"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if provisioning_id is not None:
            body["provisioningId"] = provisioning_id
        if customer_id is not None:
            body["customerId"] = customer_id
        if email is not None:
            body["email"] = email
        if package is not None:
            body["package"] = package
        _missing = [f for f in ['email'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-consent-move")
def create_consent_move(
    subscriber_id: str = typer.Argument(help="subscriberId"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Send Consent User Move Email to Pending Wholesale Subscribers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/subscribers/{subscriber_id}/emails/consentMove"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


