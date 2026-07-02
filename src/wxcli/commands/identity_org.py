import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Calling identity-org.")


@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get an organization."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}"
    try:
        result = api.session.rest_get(url)
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
    display_name: str = typer.Option(None, "--display-name", help="New full name of the organization."),
    preferred_language: str = typer.Option(None, "--preferred-language", help="It is the default preferredLanguage for user creation in thi"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an organization\n\nExample --json-body:\n  '{"schemas":["..."],"displayName":"...","preferredLanguage":"..."}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if display_name is not None:
            body["displayName"] = display_name
        if preferred_language is not None:
            body["preferredLanguage"] = preferred_language
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("update-authentication-config")
def update_authentication_config(
    remember_my_login_id: bool = typer.Option(None, "--remember-my-login-id/--no-remember-my-login-id", help="Login Id set to true if it should be remembered."),
    remember_my_login_id_duration: str = typer.Option(None, "--remember-my-login-id-duration", help="Specifies the number of days the user's login ID is remember"),
    mfa_enabled: bool = typer.Option(None, "--mfa-enabled/--no-mfa-enabled", help="Enable/ Disable multi-factor authentication on an organizati"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Organization Authentication Configuration Settings\n\nExample --json-body:\n  '{"schemas":["..."],"RememberMyLoginId":true,"RememberMyLoginIdDuration":0,"mfaEnabled":true}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/authenticationConfig"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if remember_my_login_id is not None:
            body["RememberMyLoginId"] = remember_my_login_id
        if remember_my_login_id_duration is not None:
            body["RememberMyLoginIdDuration"] = remember_my_login_id_duration
        if mfa_enabled is not None:
            body["mfaEnabled"] = mfa_enabled
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("update-password-policy")
def update_password_policy(
    minimum_numeric: str = typer.Option(None, "--minimum-numeric", help="Minimum number of numeric characters in password"),
    minimum_cap_alpha: str = typer.Option(None, "--minimum-cap-alpha", help="Minimum number of uppercase alphabetic character letters in"),
    minimum_low_alpha: str = typer.Option(None, "--minimum-low-alpha", help="Minimum number of lowercase alphabetic character letters in"),
    minimum_special: str = typer.Option(None, "--minimum-special", help="Minimum number of special characters included \"~!@#$%^&*()-_"),
    minimum_length: str = typer.Option(None, "--minimum-length", help="Minimum length of password. Must be between 8 and 256, inclu"),
    history_count: str = typer.Option(None, "--history-count", help="The number of former passwords in history, the new password"),
    max_password_age: str = typer.Option(None, "--max-password-age", help="The password expired time, unit: day, that means user need t"),
    not_acceptable_strings: str = typer.Option(None, "--not-acceptable-strings", help="The password can not be any one in this string list."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Organization Password Policy\n\nExample --json-body:\n  '{"schemas":["..."],"minimumNumeric":"...","minimumCapAlpha":"...","minimumLowAlpha":"...","minimumSpecial":"...","minimumLength":"...","historyCount":"...","maxPasswordAge":"..."}'."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/passwordPolicy"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if minimum_numeric is not None:
            body["minimumNumeric"] = minimum_numeric
        if minimum_cap_alpha is not None:
            body["minimumCapAlpha"] = minimum_cap_alpha
        if minimum_low_alpha is not None:
            body["minimumLowAlpha"] = minimum_low_alpha
        if minimum_special is not None:
            body["minimumSpecial"] = minimum_special
        if minimum_length is not None:
            body["minimumLength"] = minimum_length
        if history_count is not None:
            body["historyCount"] = history_count
        if max_password_age is not None:
            body["maxPasswordAge"] = max_password_age
        if not_acceptable_strings is not None:
            body["notAcceptableStrings"] = not_acceptable_strings
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("generate-otp")
def generate_otp(
    user_id: str = typer.Argument(help="userId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate OTP."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/users/{user_id}/actions/generateOtp"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    print_json(result)


