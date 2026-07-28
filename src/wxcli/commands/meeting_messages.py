import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-messages.")


@app.command("delete", short_help="Delete a Meeting Message.")
def delete(
    meeting_message_id: str = typer.Argument(help="Webex MEETING_MESSAGE id, from: wxcli messages list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Message.\n\n\b\nExample: wxcli meeting-messages delete MEETING_MESSAGE_ID"""
    if not force:
        typer.confirm(f"Delete {meeting_message_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meeting/messages/{meeting_message_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {meeting_message_id}")
    else:
        emit({"status": "deleted", "id": meeting_message_id}, output=output, fields=fields)


