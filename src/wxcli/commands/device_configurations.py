import json
import typer
from wxcli.errors import WebexError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling device-configurations.")


@app.command("show")
def show(
    device_id: str = typer.Option(..., "--device-id", help="List device configurations by device ID."),
    key: str = typer.Option(None, "--key", help="This can optionally be used to filter configurations. Keys a"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Device Configurations for device."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/deviceConfigurations"
    params = {}
    if device_id is not None:
        params["deviceId"] = device_id
    if key is not None:
        params["key"] = key
    try:
        result = api.session.rest_get(url, params=params)
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
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update")
def update(
    device_id: str = typer.Option(..., "--device-id", help="Update device configurations by device ID."),
    op: str = typer.Option(None, "--op", help="Choices: remove, replace"),
    path: str = typer.Option(None, "--path", help="Only paths ending in `/sources/configured/value` are support"),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Configurations."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/deviceConfigurations"
    params = {}
    if device_id is not None:
        params["deviceId"] = device_id
    if json_body:
        body = json.loads(json_body)
    else:
        patch_op = {}
        if op is not None:
            patch_op["op"] = op
        if path is not None:
            patch_op["path"] = path
        if value is not None:
            try:
                patch_op["value"] = json.loads(value)
            except json.JSONDecodeError:
                patch_op["value"] = value
        body = [patch_op]
    try:
        result = api.session.rest_patch(url, json=body, params=params, content_type="application/json-patch+json")
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
    typer.echo(f"Updated.")


