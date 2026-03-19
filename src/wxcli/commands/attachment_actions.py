import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling attachment-actions.")


@app.command("create-an-attachment")
def create_an_attachment(
    type_param: str = typer.Option(None, "--type", help="Choices: submit"),
    message_id: str = typer.Option(None, "--message-id", help="The ID of the message which contains the attachment."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Attachment Action."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/attachment/actions"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
        if message_id is not None:
            body["messageId"] = message_id
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



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Attachment Action Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/attachment/actions/{id}"
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


