import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling events.")


@app.command("list")
def cmd_list(
    resource: str = typer.Option(None, "--resource", help="List events with a specific resource type. (use --help for choices)"),
    type_param: str = typer.Option(None, "--type", help="Choices: created, updated, deleted, ended"),
    actor_id: str = typer.Option(None, "--actor-id", help="List events performed by this person, by person ID."),
    from_param: str = typer.Option(None, "--from", help="List events which occurred after a specific date and time."),
    to: str = typer.Option(None, "--to", help="List events that occurred before a specific date and time. I"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: calling"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    event_id: str = typer.Argument(help="eventId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Event Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/events/{event_id}"
    try:
        result = api.session.rest_get(url)
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


