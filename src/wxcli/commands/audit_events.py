import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling admin-audit-events.")


@app.command("list")
def cmd_list(
    from_param: str = typer.Option(None, "--from", help="List events which occurred after a specific date and time."),
    to: str = typer.Option(None, "--to", help="List events which occurred before a specific date and time."),
    actor_id: str = typer.Option(None, "--actor-id", help="List events performed by this person, by ID."),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of events in the response. The maxi"),
    offset: str = typer.Option(None, "--offset", help="Offset from the first result that you want to fetch."),
    event_categories: str = typer.Option(None, "--event-categories", help="List events, by event categories."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Admin Audit Events."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/adminAudit/events"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if actor_id is not None:
        params["actorId"] = actor_id
    if max is not None:
        params["max"] = max
    if offset is not None:
        params["offset"] = offset
    if event_categories is not None:
        params["eventCategories"] = event_categories
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



@app.command("list-event-categories")
def list_event_categories(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Admin Audit Event Categories."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/adminAudit/eventCategories"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("eventCategories", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


