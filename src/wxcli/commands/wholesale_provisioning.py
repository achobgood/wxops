import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling wholesale-provisioning.")


@app.command("list", short_help="List Wholesale Customers.")
def cmd_list(
    external_id: str = typer.Option(None, "--external-id", help="Customer external ID."),
    status: str = typer.Option(None, "--status", help="Customer API status."),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('External ID', 'externalId'), ('Status', 'status')], limit=limit)



_BODY_SKELETON_CREATE = '{"provisioningId":"...","packages":["common_area_calling"],"externalId":"...","address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"orgId":"...","customerInfo":{"name":"...","primaryEmail":"...","language":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}},"subPartnerAdminEmail":"..."}'

@app.command("create", short_help="Provision a Wholesale Customer.")
def create(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="(required) This Provisioning ID defines how this customer is to be provisioned for Webex Services. Each Customer Template will have their own unique Provisioning ID. This ID will be displayed under the chosen Customer Template on [Webex Control Hub](https://admin.webex.com)."),
    org_id: str = typer.Option(None, "--org-id", help="The organization ID of the enterprise in Webex. Mandatory for existing customers."),
    external_id: str = typer.Option(None, "--external-id", help="(required) External ID of the Wholesale customer."),
    sub_partner_admin_email: str = typer.Option(None, "--sub-partner-admin-email", help="The email of the sub partner organization admin."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Provision a Wholesale Customer.\n\n\b\nExample: wxcli wholesale-provisioning create --provisioning-id PROVISIONING_ID --external-id EXTERNAL_ID\n\n\b\nExample --json-body: '{"provisioningId":"...","packages":["common_area_calling"],"externalId":"...","address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"orgId":"...","customerInfo":{"name":"...","primaryEmail":"...","language":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}},"subPartnerAdminEmail":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show", short_help="Get a Wholesale Customer.")
def show(
    customer_id: str = typer.Argument(help="Webex ENTERPRISE id, from: wxcli wholesale-provisioning list"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    include_package_license_info: str = typer.Option(None, "--include-package-license-info", help="If specified as true, a list of licenseIds will be returned for all provisioned packages"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Wholesale Customer.\n\n\b\nExample: wxcli wholesale-provisioning show CUSTOMER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers/{customer_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if include_package_license_info is not None:
        params["includePackageLicenseInfo"] = include_package_license_info
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"packages":["common_area_calling"],"externalId":"...","address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}},"subPartnerAdminEmail":"..."}'

@app.command("update", short_help="Update a Wholesale Customer.")
def update(
    customer_id: str = typer.Argument(help="Webex ENTERPRISE id, from: wxcli wholesale-provisioning list"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    external_id: str = typer.Option(None, "--external-id", help="External ID of the Wholesale customer."),
    sub_partner_admin_email: str = typer.Option(None, "--sub-partner-admin-email", help="The email of the sub partner organization admin."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Wholesale Customer.\n\n\b\nExample: wxcli wholesale-provisioning update CUSTOMER_ID\n\n\b\nExample --json-body: '{"packages":["common_area_calling"],"externalId":"...","address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}},"subPartnerAdminEmail":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers/{customer_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if external_id is not None:
            body["externalId"] = external_id
        if sub_partner_admin_email is not None:
            body["subPartnerAdminEmail"] = sub_partner_admin_email
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
        emit({"status": "updated", "id": customer_id}, output=output, fields=fields)



@app.command("delete", hidden=True)
@app.command("delete-customers", short_help="Remove a Wholesale Customer.")
def delete_customers(
    customer_id: str = typer.Argument(help="Webex ENTERPRISE id, from: wxcli wholesale-provisioning list"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove a Wholesale Customer.\n\n\b\nExample: wxcli wholesale-provisioning delete-customers CUSTOMER_ID"""
    if not force:
        typer.confirm(f"Delete {customer_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers/{customer_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {customer_id}")
    else:
        emit({"status": "removed", "id": customer_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_VALIDATE_CUSTOMERS = '{"address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"provisioningId":"...","packages":["common_area_calling"],"orgId":"...","externalId":"...","customerInfo":{"primaryEmail":"...","name":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}}}'

@app.command("create-validate-customers", short_help="Precheck a Wholesale Customer Provisioning.")
def create_validate_customers(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="Defines how this wholesale customer is to be provisioned for Cisco Webex Services. Each Customer Template will have its unique Provisioning ID. This ID will be displayed under the chosen Customer Template on Cisco Webex Control Hub."),
    org_id: str = typer.Option(None, "--org-id", help="The organization ID of the enterprise in Cisco Webex."),
    external_id: str = typer.Option(None, "--external-id", help="External ID of the Wholesale customer."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Precheck a Wholesale Customer Provisioning.\n\n\b\nExample --json-body: '{"address":{"addressLine1":"...","city":"...","country":"...","addressLine2":"...","stateOrProvince":"...","zipOrPostalCode":"..."},"provisioningId":"...","packages":["common_area_calling"],"orgId":"...","externalId":"...","customerInfo":{"primaryEmail":"...","name":"..."},"provisioningParameters":{"calling":{"location":"..."},"meetings":{"timezone":"..."},"packages":{"limits":"..."}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_VALIDATE_CUSTOMERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/customers/validate"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = load_json_body(json_body)
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



@app.command("list-sub-partners", short_help="List Wholesale Sub-partners.")
def list_sub_partners(
    provisioning_state: str = typer.Option(None, "--provisioning-state", help="Status to filter sub-partners based on provisioning state."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Subscription ID', 'subscriptionId'), ('Provisioning State', 'provisioningState'), ('Created', 'created'), ('Billing Start Date', 'billingStartDate')], limit=limit)



@app.command("list-subscribers", short_help="List Wholesale Subscribers.")
def list_subscribers(
    customer_id: str = typer.Option(None, "--customer-id", help="Wholesale customer ID."),
    person_id: str = typer.Option(None, "--person-id", help="The person ID of the subscriber used in the [/v1/people API](/docs/api/v1/people)."),
    external_customer_id: str = typer.Option(None, "--external-customer-id", help="Customer external ID."),
    email: str = typer.Option(None, "--email", help="The email address of the subscriber."),
    status: str = typer.Option(None, "--status", help="The provisioning status of the subscriber."),
    after: str = typer.Option(None, "--after", help="Only include subscribers created after this date and time. Epoch time (in milliseconds) preferred, but ISO 8601 date format also accepted."),
    last_status_change: str = typer.Option(None, "--last-status-change", help="Only include subscribers with a provisioning status change after this date and time. Epoch time (in milliseconds) preferred, but ISO 8601 date format also accepted."),
    sort_by: str = typer.Option(None, "--sort-by", help="Supported `sortBy` attributes are `created` and `lastStatusChange`. Default is `created`."),
    sort_order: str = typer.Option(None, "--sort-order", help="Sort by `ASC` (ascending) or `DESC` (descending)."),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Email', 'email'), ('Person ID', 'personId'), ('Customer ID', 'customerId'), ('External Customer ID', 'externalCustomerId')], limit=limit)



_BODY_SKELETON_CREATE_SUBSCRIBERS = '{"customerId":"...","email":"...","provisioningParameters":{"firstName":"...","lastName":"...","primaryPhoneNumber":"...","extension":"...","locationId":"..."},"package":"webex_calling","packages":["webex_calling"]}'

@app.command("create-subscribers", short_help="Provision a Wholesale Subscriber.")
def create_subscribers(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    customer_id: str = typer.Option(None, "--customer-id", help="(required) ID of the Provisioned Customer for Webex Wholesale."),
    email: str = typer.Option(None, "--email", help="(required) The email address of the subscriber (mandatory for the trusted email provisioning flow)."),
    package: str = typer.Option(None, "--package", help="Choices: webex_calling, webex_meetings, webex_suite, webex_voice, cx_essentials, webex_calling_standard"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Provision a Wholesale Subscriber.\n\n\b\nExample: wxcli wholesale-provisioning create-subscribers --customer-id CUSTOMER_ID --email EMAIL\n\n\b\nExample --json-body: '{"customerId":"...","email":"...","provisioningParameters":{"firstName":"...","lastName":"...","primaryPhoneNumber":"...","extension":"...","locationId":"..."},"package":"webex_calling","packages":["webex_calling"]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SUBSCRIBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show-subscribers", short_help="Get a Wholesale Subscriber.")
def show_subscribers(
    subscriber_id: str = typer.Argument(help="Webex SUBSCRIBER id, from: wxcli wholesale-provisioning list-subscribers"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Wholesale Subscriber.\n\n\b\nExample: wxcli wholesale-provisioning show-subscribers SUBSCRIBER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers/{subscriber_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SUBSCRIBERS = '{"package":"webex_calling","packages":["webex_calling"],"provisioningParameters":{"primaryPhoneNumber":"...","extension":"...","locationId":"..."}}'

@app.command("update-subscribers", short_help="Update a Wholesale Subscriber.")
def update_subscribers(
    subscriber_id: str = typer.Argument(help="Webex SUBSCRIBER id, from: wxcli wholesale-provisioning list-subscribers"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    package: str = typer.Option(None, "--package", help="Choices: webex_calling, webex_meetings, webex_suite, webex_voice, cx_essentials, webex_calling_standard, attendant_console, cx_premium_agent, cx_standard_agent"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Wholesale Subscriber.\n\n\b\nExample: wxcli wholesale-provisioning update-subscribers SUBSCRIBER_ID\n\n\b\nExample --json-body: '{"package":"webex_calling","packages":["webex_calling"],"provisioningParameters":{"primaryPhoneNumber":"...","extension":"...","locationId":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SUBSCRIBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers/{subscriber_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if package is not None:
            body["package"] = package
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
        emit({"status": "updated", "id": subscriber_id}, output=output, fields=fields)



@app.command("delete-subscribers", short_help="Remove a Wholesale Subscriber.")
def delete_subscribers(
    subscriber_id: str = typer.Argument(help="Webex SUBSCRIBER id, from: wxcli wholesale-provisioning list-subscribers"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove a Wholesale Subscriber.\n\n\b\nExample: wxcli wholesale-provisioning delete-subscribers SUBSCRIBER_ID"""
    if not force:
        typer.confirm(f"Delete {subscriber_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers/{subscriber_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {subscriber_id}")
    else:
        emit({"status": "removed", "id": subscriber_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_VALIDATE_SUBSCRIBERS = '{"email":"...","provisioningId":"...","customerId":"...","package":"webex_calling","packages":["webex_calling"],"provisioningParameters":{"firstName":"...","lastName":"...","primaryPhoneNumber":"...","extension":"...","locationId":"..."},"customerInfo":{"primaryEmail":"..."}}'

@app.command("create-validate-subscribers", short_help="Precheck a Wholesale Subscriber Provisioning.")
def create_validate_subscribers(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="Defines how this wholesale subscriber is to be provisioned for Cisco Webex Services. Each Customer template has its unique provisioning ID. This ID is displayed under the chosen customer template on Cisco Webex Control Hub."),
    customer_id: str = typer.Option(None, "--customer-id", help="ID of the Provisioned Customer for Webex Wholesale."),
    email: str = typer.Option(None, "--email", help="(required) The email address of the subscriber."),
    package: str = typer.Option(None, "--package", help="Choices: webex_calling, webex_meetings, webex_suite, webex_voice, cx_essentials, webex_calling_standard"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Precheck a Wholesale Subscriber Provisioning.\n\n\b\nExample: wxcli wholesale-provisioning create-validate-subscribers --email EMAIL\n\n\b\nExample --json-body: '{"email":"...","provisioningId":"...","customerId":"...","package":"webex_calling","packages":["webex_calling"],"provisioningParameters":{"firstName":"...","lastName":"...","primaryPhoneNumber":"...","extension":"...","locationId":"..."},"customerInfo":{"primaryEmail":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_VALIDATE_SUBSCRIBERS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/subscribers/validate"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = load_json_body(json_body)
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



@app.command("create-consent-move", short_help="Send Consent User Move Email to Pending Wholesale Subscribers.")
def create_consent_move(
    subscriber_id: str = typer.Argument(help="Webex SUBSCRIBER id"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Send Consent User Move Email to Pending Wholesale Subscribers.\n\n\b\nExample: wxcli wholesale-provisioning create-consent-move SUBSCRIBER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/subscribers/{subscriber_id}/emails/consentMove"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
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
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)


