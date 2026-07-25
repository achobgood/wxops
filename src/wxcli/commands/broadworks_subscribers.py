import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling broadworks-subscribers.")


@app.command("list")
def cmd_list(
    user_id: str = typer.Option(None, "--user-id", help="The user ID of the subscriber on BroadWorks."),
    person_id: str = typer.Option(None, "--person-id", help="The Person ID of the Webex subscriber."),
    email: str = typer.Option(None, "--email", help="The email address of the subscriber."),
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="The Provisioning ID associated with this subscriber."),
    sp_enterprise_id: str = typer.Option(None, "--sp-enterprise-id", help="The Service Provider supplied unique identifier for the subscriber's enterprise."),
    last_status_change: str = typer.Option(None, "--last-status-change", help="Only include subscribers with a provisioning status change after this date and time. Epoch time (in milliseconds) preferred, but ISO 8601 date format also accepted."),
    status: str = typer.Option(None, "--status", help="Choices: pending_email_input, pending_email_validation, pending_user_migration, provisioning, provisioned, updating, error"),
    after: str = typer.Option(None, "--after", help="Only include subscribers created after this date and time. Epoch time (in milliseconds) preferred, but ISO 8601 date format also accepted."),
    self_activated: str = typer.Option(None, "--self-activated", help="Indicates if the subscriber was self activated, rather than provisioned via these APIs."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List BroadWorks Subscribers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers"
    params = {}
    if user_id is not None:
        params["userId"] = user_id
    if person_id is not None:
        params["personId"] = person_id
    if email is not None:
        params["email"] = email
    if provisioning_id is not None:
        params["provisioningId"] = provisioning_id
    if sp_enterprise_id is not None:
        params["spEnterpriseId"] = sp_enterprise_id
    if last_status_change is not None:
        params["lastStatusChange"] = last_status_change
    if status is not None:
        params["status"] = status
    if after is not None:
        params["after"] = after
    if self_activated is not None:
        params["selfActivated"] = self_activated
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE = '{"provisioningId":"...","userId":"...","spEnterpriseId":"...","firstName":"...","lastName":"...","package":"softphone","primaryPhoneNumber":"...","mobilePhoneNumber":"..."}'

@app.command("create")
def create(
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="(required) This Provisioning ID defines how this subscriber is to be provisioned for Webex Services. Each Customer Template will have their own unique Provisioning ID. This ID will be displayed under the chosen Customer Template on Webex Partner Hub."),
    user_id: str = typer.Option(None, "--user-id", help="(required) The user ID of the subscriber on BroadWorks."),
    sp_enterprise_id: str = typer.Option(None, "--sp-enterprise-id", help="(required) The Service Provider supplied unique identifier for the subscriber's enterprise."),
    first_name: str = typer.Option(None, "--first-name", help="(required) The first name of the subscriber."),
    last_name: str = typer.Option(None, "--last-name", help="(required) The last name of the subscriber."),
    package: str = typer.Option(None, "--package", help="(required) Choices: softphone, basic, standard, premium"),
    primary_phone_number: str = typer.Option(None, "--primary-phone-number", help="The primary phone number configured against the subscriber on BroadWorks."),
    mobile_phone_number: str = typer.Option(None, "--mobile-phone-number", help="The mobile phone number configured against the subscriber on BroadWorks. Any empty value on update will remove the already configured mobile phone number."),
    extension: str = typer.Option(None, "--extension", help="The extension number configured against the subscriber on BroadWorks."),
    email: str = typer.Option(None, "--email", help="The email address of the subscriber (mandatory for the trusted email provisioning flow)."),
    language: str = typer.Option(None, "--language", help="The {ISO-639-1}_{ISO-3166} or {ISO-639-1} locale or language code used as preferred language for organization and Webex Meeting Sites. Refer to the [help..."),
    timezone: str = typer.Option(None, "--timezone", help="The time zone associated with the subscriber. Refer to the [Webex Meetings Site Timezone](/docs/api/guides/webex-for-broadworks-developers-guide#webex-meetings-site-timezone) section of the [Webex for BroadWorks](/docs/api/guides/webex-for-broadworks-developers-guide) guide for more information."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Provision a BroadWorks Subscriber\n\nExample --json-body:\n  '{"provisioningId":"...","userId":"...","spEnterpriseId":"...","firstName":"...","lastName":"...","package":"softphone","primaryPhoneNumber":"...","mobilePhoneNumber":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if provisioning_id is not None:
            body["provisioningId"] = provisioning_id
        if user_id is not None:
            body["userId"] = user_id
        if sp_enterprise_id is not None:
            body["spEnterpriseId"] = sp_enterprise_id
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if package is not None:
            body["package"] = package
        if primary_phone_number is not None:
            body["primaryPhoneNumber"] = primary_phone_number
        if mobile_phone_number is not None:
            body["mobilePhoneNumber"] = mobile_phone_number
        if extension is not None:
            body["extension"] = extension
        if email is not None:
            body["email"] = email
        if language is not None:
            body["language"] = language
        if timezone is not None:
            body["timezone"] = timezone
        _missing = [f for f in ['provisioningId', 'userId', 'spEnterpriseId', 'firstName', 'lastName', 'package'] if f not in body or body[f] is None]
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



@app.command("show")
def show(
    subscriber_id: str = typer.Argument(help="subscriberId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a BroadWorks Subscriber."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers/{subscriber_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"userId":"...","firstName":"...","lastName":"...","primaryPhoneNumber":"...","mobilePhoneNumber":"...","extension":"...","timezone":"...","package":"..."}'

@app.command("update")
def update(
    subscriber_id: str = typer.Argument(help="subscriberId"),
    user_id: str = typer.Option(None, "--user-id", help="The user ID of the subscriber on BroadWorks."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the subscriber."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the subscriber."),
    primary_phone_number: str = typer.Option(None, "--primary-phone-number", help="The primary phone number configured against the subscriber on BroadWorks. Any empty value on update will remove the already configured primary phone number if an extension is set. The user must have either a primary phone number or an extension configured."),
    mobile_phone_number: str = typer.Option(None, "--mobile-phone-number", help="The mobile phone number configured against the subscriber on BroadWorks. Any empty value on update will remove the already configured mobile phone number."),
    extension: str = typer.Option(None, "--extension", help="The extension number configured against the subscriber on BroadWorks. Any empty value on update will remove the already configured extension if a primary phone number is set. The user must have either a primary phone number or an extension configured."),
    timezone: str = typer.Option(None, "--timezone", help="The time zone associated with the subscriber. Refer to the [Webex Meetings Site Timezone](/docs/api/guides/webex-for-broadworks-developers-guide#webex-meetings-site-timezone) section of the [Webex for BroadWorks](/docs/api/guides/webex-for-broadworks-developers-guide) guide for more information."),
    package: str = typer.Option(None, "--package", help="The Webex for BroadWorks Package to be assigned to the subscriber."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a BroadWorks Subscriber\n\nExample --json-body:\n  '{"userId":"...","firstName":"...","lastName":"...","primaryPhoneNumber":"...","mobilePhoneNumber":"...","extension":"...","timezone":"...","package":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers/{subscriber_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if user_id is not None:
            body["userId"] = user_id
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if primary_phone_number is not None:
            body["primaryPhoneNumber"] = primary_phone_number
        if mobile_phone_number is not None:
            body["mobilePhoneNumber"] = mobile_phone_number
        if extension is not None:
            body["extension"] = extension
        if timezone is not None:
            body["timezone"] = timezone
        if package is not None:
            body["package"] = package
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
        emit({"status": "updated", "id": subscriber_id}, output=output, fields=fields)



@app.command("delete")
def delete(
    subscriber_id: str = typer.Argument(help="subscriberId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove a BroadWorks Subscriber."""
    if not force:
        typer.confirm(f"Delete {subscriber_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers/{subscriber_id}"
    try:
        result = api.session.rest_delete(url)
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



_BODY_SKELETON_CREATE_VALIDATE = '{"email":"...","provisioningId":"...","userId":"...","spEnterpriseId":"...","firstName":"...","lastName":"...","package":"softphone","primaryPhoneNumber":"..."}'

@app.command("create-validate")
def create_validate(
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="Provisioning ID that defines how this subscriber is to be provisioned for Cisco Webex Services. Each Customer Template has its unique Provisioning ID. This ID will be displayed under the chosen Customer Template on Cisco Webex Control Hub."),
    user_id: str = typer.Option(None, "--user-id", help="The user ID of the Broadworks subscriber."),
    sp_enterprise_id: str = typer.Option(None, "--sp-enterprise-id", help="The Service Provider supplied unique identifier for the subscriber's enterprise."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the subscriber."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the subscriber."),
    package: str = typer.Option(None, "--package", help="Choices: softphone, basic, standard, premium"),
    primary_phone_number: str = typer.Option(None, "--primary-phone-number", help="The primary phone number configured for the subscriber on BroadWorks."),
    mobile_phone_number: str = typer.Option(None, "--mobile-phone-number", help="The mobile phone number configured against the subscriber on BroadWorks."),
    extension: str = typer.Option(None, "--extension", help="The extension number configured against the subscriber on BroadWorks."),
    email: str = typer.Option(None, "--email", help="(required) The email address of the subscriber."),
    language: str = typer.Option(None, "--language", help="The ISO 639-1 language code associated with the subscriber. Reserved for future use. Any value currently specified will be ignored during subscriber provisioning."),
    timezone: str = typer.Option(None, "--timezone", help="The time zone associated with the subscriber. Refer to the [Webex Meetings Site Timezone](/docs/api/guides/webex-for-broadworks-developers-guide#webex-meetings-site-timezone) section of the [Webex for BroadWorks](/docs/api/guides/webex-for-broadworks-developers-guide) guide for more information."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Precheck a Broadworks Subscriber Provisioning\n\nExample --json-body:\n  '{"email":"...","provisioningId":"...","userId":"...","spEnterpriseId":"...","firstName":"...","lastName":"...","package":"softphone","primaryPhoneNumber":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_VALIDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers/validate"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if provisioning_id is not None:
            body["provisioningId"] = provisioning_id
        if user_id is not None:
            body["userId"] = user_id
        if sp_enterprise_id is not None:
            body["spEnterpriseId"] = sp_enterprise_id
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if package is not None:
            body["package"] = package
        if primary_phone_number is not None:
            body["primaryPhoneNumber"] = primary_phone_number
        if mobile_phone_number is not None:
            body["mobilePhoneNumber"] = mobile_phone_number
        if extension is not None:
            body["extension"] = extension
        if email is not None:
            body["email"] = email
        if language is not None:
            body["language"] = language
        if timezone is not None:
            body["timezone"] = timezone
        _missing = [f for f in ['email'] if f not in body or body[f] is None]
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



@app.command("create-consent-move")
def create_consent_move(
    subscriber_id: str = typer.Argument(help="subscriberId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Send Consent User Move Email to Pending Broadworks Subscribers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/subscribers/{subscriber_id}/emails/consentMove"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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


