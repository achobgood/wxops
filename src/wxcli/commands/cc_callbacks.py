import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-callbacks.")


@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get scheduled callback by Id."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/v1/callbacks/organization/{org_id}/scheduled-callback/{id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    callback_number: str = typer.Option(None, "--callback-number", help=""),
    schedule_date: str = typer.Option(None, "--schedule-date", help=""),
    callback_reason: str = typer.Option(None, "--callback-reason", help=""),
    source_interaction: str = typer.Option(None, "--source-interaction", help=""),
    assignee_agent: str = typer.Option(None, "--assignee-agent", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    start_time: str = typer.Option(None, "--start-time", help=""),
    end_time: str = typer.Option(None, "--end-time", help=""),
    queue_id: str = typer.Option(None, "--queue-id", help=""),
    customer_name: str = typer.Option(None, "--customer-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update scheduled callback by Id."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/v1/callbacks/organization/{org_id}/scheduled-callback/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if callback_number is not None:
            body["callbackNumber"] = callback_number
        if schedule_date is not None:
            body["scheduleDate"] = schedule_date
        if callback_reason is not None:
            body["callbackReason"] = callback_reason
        if source_interaction is not None:
            body["sourceInteraction"] = source_interaction
        if assignee_agent is not None:
            body["assigneeAgent"] = assignee_agent
        if id_param is not None:
            body["id"] = id_param
        if timezone is not None:
            body["timezone"] = timezone
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if queue_id is not None:
            body["queueId"] = queue_id
        if customer_name is not None:
            body["customerName"] = customer_name
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete scheduled callback by Id."""
    if not force:
        typer.confirm(f"Delete {org_id}?", abort=True)
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/v1/callbacks/organization/{org_id}/scheduled-callback/{id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {org_id}")



@app.command("list")
def cmd_list(
    callback_number: str = typer.Option(None, "--callback-number", help="The callback customer number to filter the scheduled callbac"),
    assignee_agent: str = typer.Option(None, "--assignee-agent", help="The unique identifier of the agent assigned to handle the ca"),
    page: str = typer.Option(None, "--page", help="The page number to retrieve."),
    page_size: str = typer.Option(None, "--page-size", help="The number of items per page."),
    sort_by: str = typer.Option(None, "--sort-by", help="The field to sort the results by. If `sortBy` is set to `ass"),
    sort_order: str = typer.Option(None, "--sort-order", help="The order to sort the results in."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get scheduled callbacks."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/v1/callbacks/organization/{org_id}/scheduled-callback"
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
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("data", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    callback_number: str = typer.Option(None, "--callback-number", help=""),
    schedule_date: str = typer.Option(None, "--schedule-date", help=""),
    callback_reason: str = typer.Option(None, "--callback-reason", help=""),
    source_interaction: str = typer.Option(None, "--source-interaction", help=""),
    assignee_agent: str = typer.Option(None, "--assignee-agent", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    start_time: str = typer.Option(None, "--start-time", help=""),
    end_time: str = typer.Option(None, "--end-time", help=""),
    queue_id: str = typer.Option(None, "--queue-id", help=""),
    customer_name: str = typer.Option(None, "--customer-name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Schedule a Callback."""
    api = get_api(debug=debug)
    org_id = get_org_id() or api.people.me().org_id
    url = f"https://webexapis.com/v1/callbacks/organization/{org_id}/scheduled-callback"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if callback_number is not None:
            body["callbackNumber"] = callback_number
        if schedule_date is not None:
            body["scheduleDate"] = schedule_date
        if callback_reason is not None:
            body["callbackReason"] = callback_reason
        if source_interaction is not None:
            body["sourceInteraction"] = source_interaction
        if assignee_agent is not None:
            body["assigneeAgent"] = assignee_agent
        if timezone is not None:
            body["timezone"] = timezone
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        if queue_id is not None:
            body["queueId"] = queue_id
        if customer_name is not None:
            body["customerName"] = customer_name
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


