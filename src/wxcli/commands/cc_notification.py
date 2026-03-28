import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling notification.")


@app.command("create")
def create(
    is_keep_alive_enabled: bool = typer.Option(None, "--is-keep-alive-enabled/--no-is-keep-alive-enabled", help=""),
    client_type: str = typer.Option(None, "--client-type", help=""),
    allow_multi_login: bool = typer.Option(None, "--allow-multi-login/--no-allow-multi-login", help=""),
    force: bool = typer.Option(None, "--force/--no-force", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Subscribe Notification."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/notification/subscribe"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if is_keep_alive_enabled is not None:
            body["isKeepAliveEnabled"] = is_keep_alive_enabled
        if client_type is not None:
            body["clientType"] = client_type
        if allow_multi_login is not None:
            body["allowMultiLogin"] = allow_multi_login
        if force is not None:
            body["force"] = force
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


