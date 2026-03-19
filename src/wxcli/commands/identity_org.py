import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling identity-organization.")


@app.command("show")
def show(
    org_id: str = typer.Argument(help="orgId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get an organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/identity/organizations/{org_id}"
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



@app.command("update")
def update(
    org_id: str = typer.Argument(help="orgId"),
    display_name: str = typer.Option(None, "--display-name", help="New full name of the organization."),
    preferred_language: str = typer.Option(None, "--preferred-language", help="It is the default preferredLanguage for user creation in thi"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an organization."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/identity/organizations/{org_id}"
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("generate-otp")
def generate_otp(
    org_id: str = typer.Argument(help="orgId"),
    user_id: str = typer.Argument(help="userId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Generate OTP."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/identity/organizations/{org_id}/users/{user_id}/actions/generateOtp"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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


