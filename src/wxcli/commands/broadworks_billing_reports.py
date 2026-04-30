import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling broadworks-billing-reports.")


@app.command("list")
def cmd_list(
    before: str = typer.Option(None, "--before", help="Only include billing reports created before this date."),
    after: str = typer.Option(None, "--after", help="Only include billing reports created after this date."),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort the reports.  + Members:     + id     + status     + bi"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    billing_period: str = typer.Option(None, "--billing-period", help="(required) The year and month (`YYYY-MM`) for which the billing report"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a BroadWorks Billing Report."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/billing/reports"
    if json_body:
        body = json.loads(json_body)
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
    """Get a BroadWorks Billing Report."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/billing/reports/{id}"
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



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a BroadWorks Billing Report."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/billing/reports/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")


