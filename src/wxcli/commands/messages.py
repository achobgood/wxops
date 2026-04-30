import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling messages.")


@app.command("delete")
def delete(
    meeting_message_id: str = typer.Argument(help="meetingMessageId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Meeting Message."""
    if not force:
        typer.confirm(f"Delete {meeting_message_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meeting/messages/{meeting_message_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {meeting_message_id}")


