import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-queue-stats.")


@app.command("list")
def cmd_list(
    from_param: str = typer.Option(..., "--from", help="Start time for the query (in epoch milliseconds). Any epoch time can be passed in the input, from date will be rounded down to nearest 15 minute window. For example, epoch time of 12:05 will be rounded down to 12:00."),
    to: str = typer.Option(..., "--to", help="End time for the query (in epoch milliseconds). Any epoch time can be passed in the input, from date will be rounded down to nearest 15 minute window. For example, epoch time of 12:55 will be rounded down to 12:45. The difference between to and from time must be less than 24 hours (86400000..."),
    interval: str = typer.Option(None, "--interval", help="Time interval (in minutes) to chunk statistics by i.e. break up the entire from-to timeframe by this interval amount so that statistics can be viewed incrementally. Supported values are 15, 30, or 60."),
    queue_ids: str = typer.Option(None, "--queue-ids", help="Comma-separated list of queue IDs. A maximum of 100 values is permitted. If values are not provided, all queues for an organization are returned."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Queue Statistics."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/queues/statistics"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if interval is not None:
        params["interval"] = interval
    if queue_ids is not None:
        params["queueIds"] = queue_ids
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Queue ID', 'queueId'), ('Queue Name', 'queueName'), ('Interval Start Time', 'intervalStartTime'), ('Channel Type', 'channelType'), ('Total Offered Tasks', 'totalOfferedTasks')], limit=limit)


