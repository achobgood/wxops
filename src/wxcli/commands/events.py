import json
import typer
from wxc_sdk.rest import RestError
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
    max: str = typer.Option(None, "--max", help="Limit the maximum number of events in the response. Value mu"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: calling"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
    if max is not None:
        params["max"] = max
    if service_type is not None:
        params["serviceType"] = service_type
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
    items = result.get("items", result if isinstance(result, list) else [])
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)


