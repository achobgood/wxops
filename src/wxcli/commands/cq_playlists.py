import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling cq-playlists.")


@app.command("list")
def cmd_list(
    play_list_id: str = typer.Argument(help="playListId"),
    playlist_usage_type: str = typer.Option(None, "--playlist-usage-type", help="Choices: feature, location"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Playlist Usage."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/playlists/{play_list_id}/usage"
    params = {}
    if playlist_usage_type is not None:
        params["playlistUsageType"] = playlist_usage_type
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("locations", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


