import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Meetings meeting-site.")


@app.command("show", short_help="Get Meeting Common Settings Configuration.")
def show(
    site_url: str = typer.Option(None, "--site-url", help="URL of the Webex site which the API queries common settings of the meeting's configuration from. If not specified, the API will query from the site administrator's preferred site. All available Webex sites and the preferred site of the user can be retrieved by the [Get Site..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"siteOptions":{"allowCustomPersonalRoomURL":true},"defaultSchedulerOptions":{"entryAndExitTone":"NoTone","telephonySupport":"None","joinTeleconfNotPress1":true,"tollFree":true,"VoIP":true},"scheduleMeetingOptions":{"emailReminders":true},"securityOptions":{"joinBeforeHost":true,"audioBeforeHost":true,"firstAttendeeAsPresenter":true,"unlistAllMeetings":true,"requireLoginBeforeAccess":true,"allowMobileScreenCapture":true,"requireStrongPassword":true,"passwordCriteria":{"mixedCase":true,"minLength":0,"minNumeric":0,"minAlpha":0,"minSpecial":0,"disallowDynamicWebText":true,"disallowList":true,"disallowValues":["..."]}}}'

@app.command("update", short_help="Update Meeting Common Settings Configuration.")
def update(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Meeting Common Settings Configuration.\n\n\b\nExample --json-body: '{"siteOptions":{"allowCustomPersonalRoomURL":true},"defaultSchedulerOptions":{"entryAndExitTone":"NoTone","telephonySupport":"None","joinTeleconfNotPress1":true,"tollFree":true,"VoIP":true},"scheduleMeetingOptions":{"emailReminders":true},"securityOptions":{"joinBeforeHost":true,"audioBeforeHost":true,"firstAttendeeAsPresenter":true,"unlistAllMeetings":true,"requireLoginBeforeAccess":true,"allowMobileScreenCapture":true,"requireStrongPassword":true,"passwordCriteria":{"mixedCase":true,"minLength":0,"minNumeric":0,"minAlpha":0,"minSpecial":0,"disallowDynamicWebText":true,"disallowList":true,"disallowValues":["..."]}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/meeting/config/commonSettings"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)


