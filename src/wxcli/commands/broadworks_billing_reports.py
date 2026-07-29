import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling broadworks-billing-reports.")


@app.command("list", short_help="List BroadWorks Billing Reports.")
def cmd_list(
    before: str = typer.Option(None, "--before", help="Only include billing reports created before this date."),
    after: str = typer.Option(None, "--after", help="Only include billing reports created after this date."),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort the reports. + Members: + id + status + billingPeriod"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List BroadWorks Billing Reports."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/billing/reports"
    params = {}
    if before is not None:
        params["before"] = before
    if after is not None:
        params["after"] = after
    if sort_by is not None:
        params["sortBy"] = sort_by
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Billing Period', 'billingPeriod'), ('Status', 'status')], limit=limit)



_BODY_SKELETON_CREATE = '{"billingPeriod":"..."}'

@app.command("create", short_help="Create a BroadWorks Billing Report.")
def create(
    billing_period: str = typer.Option(None, "--billing-period", help="(required) The year and month (`YYYY-MM`) for which the billing report is to be generated."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a BroadWorks Billing Report.\n\n\b\nExample: wxcli broadworks-billing-reports create --billing-period BILLING_PERIOD\n\n\b\nExample --json-body: '{"billingPeriod":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/billing/reports"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if billing_period is not None:
            body["billingPeriod"] = billing_period
        _missing = [f for f in ['billingPeriod'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get a BroadWorks Billing Report.")
def show(
    id: str = typer.Argument(help="Webex BILLING_REPORT id, from: wxcli broadworks-billing-reports list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a BroadWorks Billing Report.\n\n\b\nExample: wxcli broadworks-billing-reports show ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/billing/reports/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("delete", short_help="Delete a BroadWorks Billing Report.")
def delete(
    id: str = typer.Argument(help="Webex BILLING_REPORT id, from: wxcli broadworks-billing-reports list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a BroadWorks Billing Report.\n\n\b\nExample: wxcli broadworks-billing-reports delete ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"https://webexapis.com/v1/broadworks/billing/reports/{id}"
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


