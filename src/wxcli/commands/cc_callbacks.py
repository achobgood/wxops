import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-callbacks.")


@app.command("list")
def cmd_list(
    callback_number: str = typer.Option(None, "--callback-number", help="The callback customer number to filter the scheduled callbac"),
    assignee_agent: str = typer.Option(None, "--assignee-agent", help="The unique identifier of the agent assigned to handle the ca"),
    page: str = typer.Option(None, "--page", help="The page number to retrieve."),
    page_size: str = typer.Option(None, "--page-size", help="The number of items per page."),
    sort_by: str = typer.Option(None, "--sort-by", help="Choices: customerName, scheduledTime, assignedTime"),
    sort_order: str = typer.Option(None, "--sort-order", help="Choices: asc, desc"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get scheduled callbacks."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/callbacks/organization/{org_id}/scheduled-callback"
    params = {}
    if callback_number is not None:
        params["callbackNumber"] = callback_number
    if assignee_agent is not None:
        params["assigneeAgent"] = assignee_agent
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort_order is not None:
        params["sortOrder"] = sort_order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
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



@app.command("create")
def create(
    customer_name: str = typer.Option(None, "--customer-name", help="(required) Name of the Customer for which callback has to be scheduled."),
    callback_number: str = typer.Option(None, "--callback-number", help="(required) Customer's phone number for the callback. Allows an optional"),
    timezone: str = typer.Option(None, "--timezone", help="(required) Valid IANA timezone name"),
    schedule_date: str = typer.Option(None, "--schedule-date", help="(required) Scheduled date in ISO-8601 (YYYY-MM-DD) format. This must be"),
    start_time: str = typer.Option(None, "--start-time", help="(required) Scheduled start time in ISO-8601 (HH:mm:ss) format. Start ti"),
    end_time: str = typer.Option(None, "--end-time", help="(required) Scheduled end time in ISO-8601 (HH:mm:ss) format. End time m"),
    queue_id: str = typer.Option(None, "--queue-id", help="(required) Unique identifier for the queue to which the callback is ass"),
    callback_reason: str = typer.Option(None, "--callback-reason", help="Reason for the callback request. This is optional and can be"),
    source_interaction: str = typer.Option(None, "--source-interaction", help="Source interaction ID for the callback. This is optional and"),
    assignee_agent: str = typer.Option(None, "--assignee-agent", help="The unique identifier of the specific agent (CI userId), who"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Schedule a Callback."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/callbacks/organization/{org_id}/scheduled-callback"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if customer_name is not None:
            body["customerName"] = customer_name
        if callback_number is not None:
            body["callbackNumber"] = callback_number
        if timezone is not None:
            body["timezone"] = timezone
        if schedule_date is not None:
            body["scheduleDate"] = schedule_date
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if queue_id is not None:
            body["queueId"] = queue_id
        if callback_reason is not None:
            body["callbackReason"] = callback_reason
        if source_interaction is not None:
            body["sourceInteraction"] = source_interaction
        if assignee_agent is not None:
            body["assigneeAgent"] = assignee_agent
        _missing = [f for f in ['customerName', 'callbackNumber', 'timezone', 'scheduleDate', 'startTime', 'endTime', 'queueId'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get scheduled callback by Id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/callbacks/organization/{org_id}/scheduled-callback/{id}"
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



@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update scheduled callback by Id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/callbacks/organization/{org_id}/scheduled-callback/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete scheduled callback by Id."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/callbacks/organization/{org_id}/scheduled-callback/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")


