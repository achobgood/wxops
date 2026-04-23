import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling broadworks-subscribers.")


@app.command("list")
def cmd_list(
    user_id: str = typer.Option(None, "--user-id", help="The user ID of the subscriber on BroadWorks."),
    person_id: str = typer.Option(None, "--person-id", help="The Person ID of the Webex subscriber."),
    email: str = typer.Option(None, "--email", help="The email address of the subscriber."),
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="The Provisioning ID associated with this subscriber."),
    sp_enterprise_id: str = typer.Option(None, "--sp-enterprise-id", help="The Service Provider supplied unique identifier for the subs"),
    last_status_change: str = typer.Option(None, "--last-status-change", help="Only include subscribers with a provisioning status change a"),
    status: str = typer.Option(None, "--status", help="Choices: pending_email_input, pending_email_validation, pending_user_migration, provisioning, provisioned, updating, error"),
    after: str = typer.Option(None, "--after", help="Only include subscribers created after this date and time. E"),
    self_activated: str = typer.Option(None, "--self-activated", help="Indicates if the subscriber was self activated, rather than"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="(required) This Provisioning ID defines how this subscriber is to be pr"),
    user_id: str = typer.Option(None, "--user-id", help="(required) The user ID of the subscriber on BroadWorks."),
    sp_enterprise_id: str = typer.Option(None, "--sp-enterprise-id", help="(required) The Service Provider supplied unique identifier for the subs"),
    first_name: str = typer.Option(None, "--first-name", help="(required) The first name of the subscriber."),
    last_name: str = typer.Option(None, "--last-name", help="(required) The last name of the subscriber."),
    package: str = typer.Option(None, "--package", help="(required) Choices: softphone, basic, standard, premium"),
    primary_phone_number: str = typer.Option(None, "--primary-phone-number", help="The primary phone number configured against the subscriber o"),
    mobile_phone_number: str = typer.Option(None, "--mobile-phone-number", help="The mobile phone number configured against the subscriber on"),
    extension: str = typer.Option(None, "--extension", help="The extension number configured against the subscriber on Br"),
    email: str = typer.Option(None, "--email", help="The email address of the subscriber (mandatory for the trust"),
    language: str = typer.Option(None, "--language", help="The {ISO-639-1}_{ISO-3166} or {ISO-639-1} locale or language"),
    timezone: str = typer.Option(None, "--timezone", help="The time zone associated with the subscriber. Refer to the ["),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Provision a BroadWorks Subscriber."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers"
    if json_body:
        body = json.loads(json_body)
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
    subscriber_id: str = typer.Argument(help="subscriberId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a BroadWorks Subscriber."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers/{subscriber_id}"
    try:
        result = api.session.rest_get(url)
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
    subscriber_id: str = typer.Argument(help="subscriberId"),
    user_id: str = typer.Option(None, "--user-id", help="The user ID of the subscriber on BroadWorks."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the subscriber."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the subscriber."),
    primary_phone_number: str = typer.Option(None, "--primary-phone-number", help="The primary phone number configured against the subscriber o"),
    mobile_phone_number: str = typer.Option(None, "--mobile-phone-number", help="The mobile phone number configured against the subscriber on"),
    extension: str = typer.Option(None, "--extension", help="The extension number configured against the subscriber on Br"),
    timezone: str = typer.Option(None, "--timezone", help="The time zone associated with the subscriber. Refer to the ["),
    package: str = typer.Option(None, "--package", help="The Webex for BroadWorks Package to be assigned to the subsc"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a BroadWorks Subscriber."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers/{subscriber_id}"
    if json_body:
        body = json.loads(json_body)
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
    subscriber_id: str = typer.Argument(help="subscriberId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove a BroadWorks Subscriber."""
    if not force:
        typer.confirm(f"Delete {subscriber_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers/{subscriber_id}"
    try:
        api.session.rest_delete(url)
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



@app.command("create-validate")
def create_validate(
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="Provisioning ID that defines how this subscriber is to be pr"),
    user_id: str = typer.Option(None, "--user-id", help="The user ID of the Broadworks subscriber."),
    sp_enterprise_id: str = typer.Option(None, "--sp-enterprise-id", help="The Service Provider supplied unique identifier for the subs"),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the subscriber."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the subscriber."),
    package: str = typer.Option(None, "--package", help="Choices: softphone, basic, standard, premium"),
    primary_phone_number: str = typer.Option(None, "--primary-phone-number", help="The primary phone number configured for the subscriber on Br"),
    mobile_phone_number: str = typer.Option(None, "--mobile-phone-number", help="The mobile phone number configured against the subscriber on"),
    extension: str = typer.Option(None, "--extension", help="The extension number configured against the subscriber on Br"),
    email: str = typer.Option(None, "--email", help="(required) The email address of the subscriber."),
    language: str = typer.Option(None, "--language", help="The ISO 639-1 language code associated with the subscriber."),
    timezone: str = typer.Option(None, "--timezone", help="The time zone associated with the subscriber. Refer to the ["),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Precheck a Broadworks Subscriber Provisioning\n\nExample --json-body:\n  '{"email":"...","provisioningId":"...","userId":"...","spEnterpriseId":"...","firstName":"...","lastName":"...","package":"softphone","primaryPhoneNumber":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/subscribers/validate"
    if json_body:
        body = json.loads(json_body)
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
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Send Consent User Move Email to Pending Broadworks Subscribers."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/subscribers/{subscriber_id}/emails/consentMove"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
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


