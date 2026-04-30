import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling workspace-metrics.")


@app.command("list")
def cmd_list(
    workspace_id: str = typer.Option(..., "--workspace-id", help="ID of the workspace to get metrics for."),
    metric_name: str = typer.Option(..., "--metric-name", help="Choices: soundLevel, ambientNoise, temperature, humidity, tvoc, peopleCount"),
    aggregation: str = typer.Option(None, "--aggregation", help="Choices: none, hourly, daily"),
    from_param: str = typer.Option(None, "--from", help="List only data points after a specific date and time (ISO 86"),
    to: str = typer.Option(None, "--to", help="List data points before a specific date and time (ISO 8601 t"),
    unit: str = typer.Option(None, "--unit", help="Choices: celsius, fahrenheit"),
    sort_by: str = typer.Option(None, "--sort-by", help="Choices: newestFirst, oldestFirst"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Workspace Metrics."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceMetrics"
    params = {}
    if workspace_id is not None:
        params["workspaceId"] = workspace_id
    if metric_name is not None:
        params["metricName"] = metric_name
    if aggregation is not None:
        params["aggregation"] = aggregation
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if unit is not None:
        params["unit"] = unit
    if sort_by is not None:
        params["sortBy"] = sort_by
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Start', 'start'), ('End', 'end'), ('Metric', 'metricName'), ('Value', 'value')], limit=limit)



@app.command("list-workspace-duration-metrics")
def list_workspace_duration_metrics(
    workspace_id: str = typer.Option(..., "--workspace-id", help="ID of the workspace to get metrics for."),
    aggregation: str = typer.Option(None, "--aggregation", help="Choices: hourly, daily"),
    measurement: str = typer.Option(None, "--measurement", help="Choices: timeUsed, timeBooked"),
    from_param: str = typer.Option(None, "--from", help="Include data points after a specific date and time (ISO 8601"),
    to: str = typer.Option(None, "--to", help="Include data points before a specific date and time (ISO 860"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Workspace Duration Metrics."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/workspaceDurationMetrics"
    params = {}
    if workspace_id is not None:
        params["workspaceId"] = workspace_id
    if aggregation is not None:
        params["aggregation"] = aggregation
    if measurement is not None:
        params["measurement"] = measurement
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('Start', 'start'), ('End', 'end'), ('Duration', 'duration')], limit=limit)


