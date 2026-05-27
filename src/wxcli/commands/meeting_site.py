import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Meetings meeting-site.")


@app.command("show")
def show(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API queries common settings"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Meeting Common Settings Configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/commonSettings"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
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
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Common Settings Configuration\n\nExample --json-body:\n  '{"siteOptions":{"allowCustomPersonalRoomURL":true},"defaultSchedulerOptions":{"entryAndExitTone":"NoTone","telephonySupport":"None","joinTeleconfNotPress1":true,"tollFree":true,"VoIP":true},"scheduleMeetingOptions":{"emailReminders":true},"securityOptions":{"joinBeforeHost":true,"audioBeforeHost":true,"firstAttendeeAsPresenter":true,"unlistAllMeetings":true,"requireLoginBeforeAccess":true,"allowMobileScreenCapture":true,"requireStrongPassword":true,"passwordCriteria":{"mixedCase":"...","minLength":"...","minNumeric":"...","minAlpha":"...","minSpecial":"...","disallowDynamicWebText":"...","disallowList":"...","disallowValues":"..."}}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/commonSettings"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")


