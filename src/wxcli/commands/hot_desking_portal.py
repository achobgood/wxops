import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling hot-desking-portal.")


@app.command("show")
def show(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Voice Portal Hot desking sign in details for a location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/features/hotDesking"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
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
    location_id: str = typer.Argument(help="locationId"),
    voice_portal_hot_desk_sign_in_enabled: bool = typer.Option(None, "--voice-portal-hot-desk-sign-in-enabled/--no-voice-portal-hot-desk-sign-in-enabled", help="If `true`, hot desking sign in via the Voice Portal is enabl"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Voice Portal Hot desking sign in details for a location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/features/hotDesking"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if voice_portal_hot_desk_sign_in_enabled is not None:
            body["voicePortalHotDeskSignInEnabled"] = voice_portal_hot_desk_sign_in_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
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
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
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
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if voice_portal_hot_desk_sign_in_enabled is not None:
            body["voicePortalHotDeskSignInEnabled"] = voice_portal_hot_desk_sign_in_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")


