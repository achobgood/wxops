import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling events.")


@app.command("list", short_help="List Events.")
def cmd_list(
    resource: str = typer.Option(None, "--resource", help="List events with a specific resource type. (use --help for choices)"),
    type_param: str = typer.Option(None, "--type", help="Choices: created, updated, deleted, ended"),
    actor_id: str = typer.Option(None, "--actor-id", help="List events performed by this person, by person ID."),
    from_param: str = typer.Option(None, "--from", help="List events which occurred after a specific date and time."),
    to: str = typer.Option(None, "--to", help="List events that occurred before a specific date and time. If not specified, events up to the present time will be listed. Cannot be set to a future date relative to the current time."),
    service_type: str = typer.Option(None, "--service-type", help="Choices: calling"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Events."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/events"
    params = {}
    if resource is not None:
        params["resource"] = resource
    if type_param is not None:
        params["type"] = type_param
    if actor_id is not None:
        params["actorId"] = actor_id
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if service_type is not None:
        params["serviceType"] = service_type
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Resource', 'resource'), ('Type', 'type'), ('App ID', 'appId'), ('Actor ID', 'actorId')], limit=limit)



@app.command("show", short_help="Get Event Details.")
def show(
    event_id: str = typer.Argument(help="Webex EVENT id, from: wxcli events list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Event Details.\n\n\b\nExample: wxcli events show EVENT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/events/{event_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


