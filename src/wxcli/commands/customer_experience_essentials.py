import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling customer-experience-essentials.")


@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Wrap Up Reasons."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons"
    params = {}
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
    items = result.get("reasons", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    name: str = typer.Option(None, "--name", help=""),
    description: str = typer.Option(None, "--description", help=""),
    assign_all_queues_enabled: bool = typer.Option(None, "--assign-all-queues-enabled/--no-assign-all-queues-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Wrap Up Reason."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if assign_all_queues_enabled is not None:
            body["assignAllQueuesEnabled"] = assign_all_queues_enabled
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("show")
def show(
    wrapup_reason_id: str = typer.Argument(help="wrapupReasonId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Wrap Up Reason."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/{wrapup_reason_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update")
def update(
    wrapup_reason_id: str = typer.Argument(help="wrapupReasonId"),
    name: str = typer.Option(None, "--name", help=""),
    description: str = typer.Option(None, "--description", help=""),
    assign_all_queues_enabled: bool = typer.Option(None, "--assign-all-queues-enabled/--no-assign-all-queues-enabled", help=""),
    unassign_all_queues_enabled: bool = typer.Option(None, "--unassign-all-queues-enabled/--no-unassign-all-queues-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Wrap Up Reason."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/{wrapup_reason_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if assign_all_queues_enabled is not None:
            body["assignAllQueuesEnabled"] = assign_all_queues_enabled
        if unassign_all_queues_enabled is not None:
            body["unassignAllQueuesEnabled"] = unassign_all_queues_enabled
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    wrapup_reason_id: str = typer.Argument(help="wrapupReasonId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Wrap Up Reason."""
    if not force:
        typer.confirm(f"Delete {wrapup_reason_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/{wrapup_reason_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {wrapup_reason_id}")



@app.command("validate-wrap-up")
def validate_wrap_up(
    name: str = typer.Option(None, "--name", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Validate Wrap Up Reason."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/actions/validateName/invoke"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("list-available-queues")
def list_available_queues(
    wrapup_reason_id: str = typer.Argument(help="wrapupReasonId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Available Queues."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/wrapup/reasons/{wrapup_reason_id}/availableQueues"
    params = {}
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
    items = result.get("availableQueues", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-settings")
def show_settings(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Wrap Up Reason Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/locations/{location_id}/queues/{queue_id}/wrapup/settings"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("update-settings")
def update_settings(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    default_wrapup_reason_id: str = typer.Option(None, "--default-wrapup-reason-id", help=""),
    wrapup_timer_enabled: bool = typer.Option(None, "--wrapup-timer-enabled/--no-wrapup-timer-enabled", help=""),
    wrapup_timer: str = typer.Option(None, "--wrapup-timer", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Wrap Up Reason Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/cxEssentials/locations/{location_id}/queues/{queue_id}/wrapup/settings"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if default_wrapup_reason_id is not None:
            body["defaultWrapupReasonId"] = default_wrapup_reason_id
        if wrapup_timer_enabled is not None:
            body["wrapupTimerEnabled"] = wrapup_timer_enabled
        if wrapup_timer is not None:
            body["wrapupTimer"] = wrapup_timer
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-screen-pop")
def list_screen_pop(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Screen Pop Configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/cxEssentials/screenPop"
    params = {}
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
    items = result.get("screenPop", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-screen-pop")
def update_screen_pop(
    location_id: str = typer.Argument(help="locationId"),
    queue_id: str = typer.Argument(help="queueId"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help=""),
    screen_pop_url: str = typer.Option(None, "--screen-pop-url", help=""),
    desktop_label: str = typer.Option(None, "--desktop-label", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Screen Pop Configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/cxEssentials/screenPop"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if screen_pop_url is not None:
            body["screenPopUrl"] = screen_pop_url
        if desktop_label is not None:
            body["desktopLabel"] = desktop_label
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-available-agents")
def list_available_agents(
    location_id: str = typer.Argument(help="locationId"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of available agents with Customer Expe"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Agents."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/cxEssentials/agents/availableAgents"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
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
    items = result.get("availableAgents", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


