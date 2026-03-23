import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling security-audit-events.")


@app.command("list")
def cmd_list(
    start_time: str = typer.Option(..., "--start-time", help="List events which occurred after a specific date and time."),
    end_time: str = typer.Option(..., "--end-time", help="List events which occurred before a specific date and time."),
    actor_id: str = typer.Option(None, "--actor-id", help="List events performed by this person, by ID."),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of events in the response. The maxi"),
    event_categories: str = typer.Option(None, "--event-categories", help="List events, by event categories."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Security Audit Events."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/securityAudit/events"
    params = {}
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time
    if actor_id is not None:
        params["actorId"] = actor_id
    if max is not None:
        params["max"] = max
    if event_categories is not None:
        params["eventCategories"] = event_categories
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


