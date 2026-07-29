import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling security-audit.")


@app.command("list", short_help="List Security Audit Events.")
def cmd_list(
    start_time: str = typer.Option(..., "--start-time", help="List events which occurred after a specific date and time."),
    end_time: str = typer.Option(..., "--end-time", help="List events which occurred before a specific date and time."),
    actor_id: str = typer.Option(None, "--actor-id", help="List events performed by this person, by ID."),
    event_categories: str = typer.Option(None, "--event-categories", help="List events, by event categories."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Security Audit Events.\n\n\b\nExample: wxcli security-audit list --start-time START_TIME --end-time END_TIME"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/securityAudit/events"
    params = {}
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time
    if actor_id is not None:
        params["actorId"] = actor_id
    if event_categories is not None:
        params["eventCategories"] = event_categories
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Created', 'created'), ('Actor Org ID', 'actorOrgId'), ('Actor ID', 'actorId')], limit=limit)


