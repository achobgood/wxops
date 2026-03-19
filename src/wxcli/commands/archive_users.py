import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling archive-users.")


@app.command("show")
def show(
    org_id: str = typer.Argument(help="orgId"),
    useruuid: str = typer.Argument(help="useruuid"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Archive User."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/identity/organizations/{org_id}/v1/ArchivedUser/{useruuid}"
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


