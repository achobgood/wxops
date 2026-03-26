import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.errors import handle_rest_error
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling reports-detailed-call-history.")


@app.command("list")
def cmd_list(
    start_time: str = typer.Option(..., "--start-time", help="Time of the first report you wish to collect. (Report time i"),
    end_time: str = typer.Option(..., "--end-time", help="Time of the last report you wish to collect. (Report time is"),
    locations: str = typer.Option(None, "--locations", help="Name of the location (as shown in Control Hub). Up to 10 com"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of reports per page of the response"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Detailed Call History."""
    api = get_api(debug=debug)
    url = f"https://analytics-calling.webexapis.com/v1/cdr_feed"
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
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Start Time', 'startTime'), ('Calling Number', 'callingNumber'), ('Called Number', 'calledNumber'), ('Duration', 'duration'), ('Direction', 'direction'), ('Call Type', 'callType')], limit=limit)



@app.command("list-cdr_stream")
def list_cdr_stream(
    start_time: str = typer.Option(..., "--start-time", help="The start date-time of the first record you wish to collect"),
    end_time: str = typer.Option(..., "--end-time", help="The end date-time of the last record you wish to collect in"),
    locations: str = typer.Option(None, "--locations", help="Name of the location (as shown in Control Hub). Up to 10 com"),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of reports per page of the response"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Live Stream Detailed Call History."""
    api = get_api(debug=debug)
    url = f"https://analytics-calling.webexapis.com/v1/cdr_stream"
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
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Start Time', 'startTime'), ('Calling Number', 'callingNumber'), ('Called Number', 'calledNumber'), ('Duration', 'duration'), ('Direction', 'direction'), ('Call Type', 'callType')], limit=limit)


