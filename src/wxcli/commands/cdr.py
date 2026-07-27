import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling cdr.")


@app.command("list")
def cmd_list(
    start_time: str = typer.Option(..., "--start-time", help="Time of the first report you wish to collect. (Report time is the time the call finished). **Note:** The specified time must be between 5 minutes ago and 48 hours ago, and formatted as `YYYY-MM-DDTHH:MM:SS.mmmZ`."),
    end_time: str = typer.Option(..., "--end-time", help="Time of the last report you wish to collect. (Report time is the time the call finished). **Note:** The specified time should be later than `startTime` but no later than 48 hours, and formatted as `YYYY-MM-DDTHH:MM:SS.mmmZ`."),
    locations: str = typer.Option(None, "--locations", help="Name of the location (as shown in Control Hub). Up to 10 comma-separated locations can be provided. Allows you to query reports by location."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    emit(items, output=output, fields=fields, columns=[('Start Time', 'Start time'), ('Calling Number', 'Calling number'), ('Called Number', 'Called number'), ('Duration', 'Duration'), ('Direction', 'Direction'), ('Call Type', 'Call type')], limit=limit)



@app.command("list-cdr_stream")
def list_cdr_stream(
    start_time: str = typer.Option(..., "--start-time", help="The start date-time of the first record you wish to collect in UTC time. It would be the earliest time at which the data was inserted into the Webex Calling cloud for the records you wish to collect. Format must be as `YYYY-MM-DDTHH:MM:SS.mmmZ`. `startTime` can't be older than 12 hours from your..."),
    end_time: str = typer.Option(..., "--end-time", help="The end date-time of the last record you wish to collect in UTC time. It would be the latest time at which the data was inserted into the Webex Calling cloud for the records you wish to collect. Format must be as `YYYY-MM-DDTHH:MM:SS.mmmZ`. `endTime` must be 1 minute ago from your current UTC time..."),
    locations: str = typer.Option(None, "--locations", help="Name of the location (as shown in Control Hub). Up to 10 comma-separated locations can be provided. Allows you to query reports by location."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    emit(items, output=output, fields=fields, columns=[('Start Time', 'Start time'), ('Calling Number', 'Calling number'), ('Called Number', 'Called number'), ('Duration', 'Duration'), ('Direction', 'Direction'), ('Call Type', 'Call type')], limit=limit)


