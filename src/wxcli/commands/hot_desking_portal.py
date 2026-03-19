import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling hot-desking-sign-in-via-voice-portal.")


@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Voice Portal Hot desking sign in details for a location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/features/hotDesking"
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



@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    voice_portal_hot_desk_sign_in_enabled: bool = typer.Option(None, "--voice-portal-hot-desk-sign-in-enabled/--no-voice-portal-hot-desk-sign-in-enabled", help="If `true`, hot desking sign in via the Voice Portal is enabl"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voice Portal Hot desking sign in details for a location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/features/hotDesking"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if voice_portal_hot_desk_sign_in_enabled is not None:
            body["voicePortalHotDeskSignInEnabled"] = voice_portal_hot_desk_sign_in_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("show-guest")
def show_guest(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Voice Portal Hot desking sign in details for a user."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/guest"
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



@app.command("update-guest")
def update_guest(
    person_id: str = typer.Argument(help="personId"),
    voice_portal_hot_desk_sign_in_enabled: bool = typer.Option(None, "--voice-portal-hot-desk-sign-in-enabled/--no-voice-portal-hot-desk-sign-in-enabled", help="If `true`, hot desking sign in via the Voice Portal is enabl"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voice Portal Hot desking sign in details for a user."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/people/{person_id}/features/hotDesking/guest"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if voice_portal_hot_desk_sign_in_enabled is not None:
            body["voicePortalHotDeskSignInEnabled"] = voice_portal_hot_desk_sign_in_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")


