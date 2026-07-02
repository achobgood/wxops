import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling person-call-settings.")


@app.command("list")
def cmd_list(
    person_id: str = typer.Argument(help="personId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve a Person's Monitoring Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/monitoring"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("monitoredElements", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update")
def update(
    person_id: str = typer.Argument(help="personId"),
    enable_call_park_notification: bool = typer.Option(None, "--enable-call-park-notification/--no-enable-call-park-notification", help="Call park notification is enabled or disabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify Monitoring Settings for a Person\n\nExample --json-body:\n  '{"enableCallParkNotification":true,"monitoredElements":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/monitoring"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enable_call_park_notification is not None:
            body["enableCallParkNotification"] = enable_call_park_notification
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")


