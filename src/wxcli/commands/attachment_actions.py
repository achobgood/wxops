import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling attachment-actions.")


_BODY_SKELETON_CREATE_AN_ATTACHMENT = '{"type":"submit","messageId":"...","inputs":{"Name":"...","Url":"...","Email":"...","Tel":"..."}}'

@app.command("create-an-attachment", short_help="Create an Attachment Action.")
def create_an_attachment(
    type_param: str = typer.Option(None, "--type", help="Choices: submit"),
    message_id: str = typer.Option(None, "--message-id", help="The ID of the message which contains the attachment."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Attachment Action.\n\n\b\nExample: wxcli attachment-actions create-an-attachment --json-body '{"type":"submit","messageId":"...","inputs":{"Name":"...","Url":"...","Email":"...","Tel":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_AN_ATTACHMENT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/attachment/actions"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
        if message_id is not None:
            body["messageId"] = message_id
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show", short_help="Get Attachment Action Details.")
def show(
    id: str = typer.Argument(help="Webex ORGANIZATION id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Attachment Action Details.\n\n\b\nExample: wxcli attachment-actions show ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/attachment/actions/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


