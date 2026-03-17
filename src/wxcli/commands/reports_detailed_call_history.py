import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling reports-detailed-call-history.")


@app.command("list")
def cmd_list(
    start_time: str = typer.Option(None, "--start-time", help="Time of the first report you wish to collect. (Report time i"),
    end_time: str = typer.Option(None, "--end-time", help="Time of the last report you wish to collect. (Report time is"),
    locations: str = typer.Option(None, "--locations", help="Name of the location (as shown in Control Hub). Up to 10 com"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of reports per page of the response"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Detailed Call History."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/cdr_feed"
    params = {}
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time
    if locations is not None:
        params["locations"] = locations
    if max is not None:
        params["max"] = max
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
    items = result.get("cdr_feed", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-cdr_stream")
def list_cdr_stream(
    start_time: str = typer.Option(None, "--start-time", help="The start date-time of the first record you wish to collect"),
    end_time: str = typer.Option(None, "--end-time", help="The end date-time of the last record you wish to collect in"),
    locations: str = typer.Option(None, "--locations", help="Name of the location (as shown in Control Hub). Up to 10 com"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of reports per page of the response"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Live Stream Detailed Call History."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/cdr_stream"
    params = {}
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time
    if locations is not None:
        params["locations"] = locations
    if max is not None:
        params["max"] = max
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
    items = result.get("cdr_stream", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


