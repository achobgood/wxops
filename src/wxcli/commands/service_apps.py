import json
import typer
from wxcli.errors import WebexError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling service-apps.")


@app.command("create")
def create(
    application_id: str = typer.Argument(help="applicationId"),
    client_id: str = typer.Option(None, "--client-id", help="(required) The OAuth client ID of the Service App"),
    client_secret: str = typer.Option(None, "--client-secret", help="(required) The OAuth client secret of the Service App"),
    target_org_id: str = typer.Option(None, "--target-org-id", help="(required) The organization ID for which the token will be created"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Service App Access Token."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/applications/{application_id}/token"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if client_id is not None:
            body["clientId"] = client_id
        if client_secret is not None:
            body["clientSecret"] = client_secret
        if target_org_id is not None:
            body["targetOrgId"] = target_org_id
        _missing = [f for f in ['clientId', 'clientSecret', 'targetOrgId'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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


