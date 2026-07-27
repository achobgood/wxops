import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-callbacks.")


@app.command("list")
def cmd_list(
    callback_number: str = typer.Option(None, "--callback-number", help="The callback customer number to filter the scheduled callbacks. Only an exact match will yield the result. Allows an optional country code followed by digits (0-9) and the special characters: space, hyphen -, parentheses ( and ), and period ., ensuring the total length is between 7 and 15..."),
    assignee_agent: str = typer.Option(None, "--assignee-agent", help="The unique identifier of the agent assigned to handle the callback. Must be in UUID format. This parameter is optional, but at least one of assigneeAgent or callbackNumber must be provided."),
    page: str = typer.Option(None, "--page", help="The page number to retrieve."),
    page_size: str = typer.Option(None, "--page-size", help="The number of items per page."),
    sort_by: str = typer.Option(None, "--sort-by", help="Choices: customerName, scheduledTime, assignedTime"),
    sort_order: str = typer.Option(None, "--sort-order", help="Choices: asc, desc"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Customer Name', 'customerName'), ('Callback Number', 'callbackNumber'), ('Timezone', 'timezone'), ('Schedule Date', 'scheduleDate')], limit=limit)



_BODY_SKELETON_CREATE = '{"customerName":"...","callbackNumber":"...","timezone":"...","scheduleDate":"...","startTime":"...","endTime":"...","queueId":"...","callbackReason":"..."}'

@app.command("create")
def create(
    customer_name: str = typer.Option(None, "--customer-name", help="(required) Name of the Customer for which callback has to be scheduled. Max customer name length should be 250 character"),
    callback_number: str = typer.Option(None, "--callback-number", help="(required) Customer's phone number for the callback. Allows an optional country code followed by digits (0-9) and the special characters: space, hyphen -, parentheses ( and ), and period ., ensuring the total length is between 7 and 15 characters."),
    timezone: str = typer.Option(None, "--timezone", help="(required) Valid IANA timezone name"),
    schedule_date: str = typer.Option(None, "--schedule-date", help="(required) Scheduled date in ISO-8601 (YYYY-MM-DD) format. This must be a valid date in local time zone and within 31 days from current date"),
    start_time: str = typer.Option(None, "--start-time", help="(required) Scheduled start time in ISO-8601 (HH:mm:ss) format. Start time must be at least 30 minutes in the future from current time."),
    end_time: str = typer.Option(None, "--end-time", help="(required) Scheduled end time in ISO-8601 (HH:mm:ss) format. End time must be at least 30 minutes after the startTime and must not exceed 8 hours after startTime."),
    queue_id: str = typer.Option(None, "--queue-id", help="(required) Unique identifier for the queue to which the callback is associated."),
    callback_reason: str = typer.Option(None, "--callback-reason", help="Reason for the callback request. This is optional and can be used to provide additional context."),
    source_interaction: str = typer.Option(None, "--source-interaction", help="Source interaction ID for the callback. This is optional and can be used to link the callback to a specific interaction. This should be a valid UUID."),
    assignee_agent: str = typer.Option(None, "--assignee-agent", help="The unique identifier of the specific agent (CI userId), who should be assigned to handle the callback. This field is optional and is primarily used for personal callbacks."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Schedule a Callback\n\nExample --json-body:\n  '{"customerName":"...","callbackNumber":"...","timezone":"...","scheduleDate":"...","startTime":"...","endTime":"...","queueId":"...","callbackReason":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/callbacks/organization/{org_id}/scheduled-callback"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update scheduled callback by Id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/callbacks/organization/{org_id}/scheduled-callback/{id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)


