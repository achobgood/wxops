import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling: cq-playlists.")


@app.command("list", short_help="Get Playlist Usage.")
def cmd_list(
    play_list_id: str = typer.Argument(help="Webex PLAYLIST id, from: wxcli announcement-playlists list"),
    playlist_usage_type: str = typer.Option(None, "--playlist-usage-type", help="Choices: feature, location"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Playlist Usage.\n\n\b\nExample: wxcli cq-playlists list PLAY_LIST_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/announcements/playlists/{play_list_id}/usage"
    params = {}
    if playlist_usage_type is not None:
        params["playlistUsageType"] = playlist_usage_type
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


