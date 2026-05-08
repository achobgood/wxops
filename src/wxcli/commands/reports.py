import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling reports.")


@app.command("list")
def cmd_list(
    report_id: str = typer.Option(None, "--report-id", help="List reports by ID."),
    service: str = typer.Option(None, "--service", help="List reports which use this service."),
    template_id: str = typer.Option(None, "--template-id", help="List reports with this report template ID."),
    from_param: str = typer.Option(None, "--from", help="List reports that were created on or after this date."),
    to: str = typer.Option(None, "--to", help="List reports that were created before this date."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Reports."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/reports"
    params = {}
    if report_id is not None:
        params["reportId"] = report_id
    if service is not None:
        params["service"] = service
    if template_id is not None:
        params["templateId"] = template_id
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    result = result or []
    items = result.get("Report Attributes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    template_id: str = typer.Option(None, "--template-id", help="(required) Unique ID representing valid report templates."),
    start_date: str = typer.Option(None, "--start-date", help="Data in the report will be from this date onwards."),
    end_date: str = typer.Option(None, "--end-date", help="Data in the report will be until this date."),
    site_list: str = typer.Option(None, "--site-list", help="Sites belonging to user's organization. This attribute is ne"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Report."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/reports"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if template_id is not None:
            body["templateId"] = template_id
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if site_list is not None:
            body["siteList"] = site_list
        _missing = [f for f in ['templateId'] if f not in body or body[f] is None]
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
    report_id: str = typer.Argument(help="reportId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Report Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/reports/{report_id}"
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
    report_id: str = typer.Argument(help="reportId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Report."""
    if not force:
        typer.confirm(f"Delete {report_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/reports/{report_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {report_id}")


