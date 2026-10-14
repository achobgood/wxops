import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Devices: workspace-metrics.")


@app.command("list", short_help="Workspace Metrics.")
def cmd_list(
    workspace_id: str = typer.Option(..., "--workspace-id", help="ID of the workspace to get metrics for."),
    metric_name: str = typer.Option(..., "--metric-name", help="Choices: soundLevel, ambientNoise, temperature, humidity, tvoc, peopleCount"),
    aggregation: str = typer.Option(None, "--aggregation", help="Choices: none, hourly, daily"),
    from_param: str = typer.Option(None, "--from", help="List only data points after a specific date and time (ISO 8601 timestamp)"),
    to: str = typer.Option(None, "--to", help="List data points before a specific date and time (ISO 8601 timestamp)"),
    unit: str = typer.Option(None, "--unit", help="Choices: celsius, fahrenheit"),
    sort_by: str = typer.Option(None, "--sort-by", help="Choices: newestFirst, oldestFirst"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Workspace Metrics.\n\n\b\nExample: wxcli workspace-metrics list --workspace-id WORKSPACE_ID --metric-name soundLevel"""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-workspace-duration-metrics", short_help="Workspace Duration Metrics.")
def list_workspace_duration_metrics(
    workspace_id: str = typer.Option(..., "--workspace-id", help="ID of the workspace to get metrics for."),
    aggregation: str = typer.Option(None, "--aggregation", help="Choices: hourly, daily"),
    measurement: str = typer.Option(None, "--measurement", help="Choices: timeUsed, timeBooked"),
    from_param: str = typer.Option(None, "--from", help="Include data points after a specific date and time (ISO 8601 timestamp)."),
    to: str = typer.Option(None, "--to", help="Include data points before a specific date and time (ISO 8601 timestamp)."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Workspace Duration Metrics.\n\n\b\nExample: wxcli workspace-metrics list-workspace-duration-metrics --workspace-id WORKSPACE_ID"""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


