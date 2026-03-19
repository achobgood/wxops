import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling meeting-qualities.")


@app.command("list")
def cmd_list(
    meeting_id: str = typer.Option(None, "--meeting-id", help="Unique identifier for the specific meeting instance. **Note:"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of media sessions in the response."),
    offset: str = typer.Option(None, "--offset", help="Offset from the first result that you want to fetch."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Qualities."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/meeting/qualities"
    params = {}
    if meeting_id is not None:
        params["meetingId"] = meeting_id
    if max is not None:
        params["max"] = max
    if offset is not None:
        params["offset"] = offset
    if limit > 0:
        params["max"] = limit
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


