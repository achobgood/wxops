import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-queue-stats.")


@app.command("list")
def cmd_list(
    from_param: str = typer.Option(..., "--from", help="Start time for the query (in epoch milliseconds). Any epoch"),
    to: str = typer.Option(..., "--to", help="End time for the query (in epoch milliseconds). Any epoch ti"),
    interval: str = typer.Option(None, "--interval", help="Time interval (in minutes) to chunk statistics by i.e. break"),
    queue_ids: str = typer.Option(None, "--queue-ids", help="Comma-separated list of queue IDs. A maximum of 100 values i"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


