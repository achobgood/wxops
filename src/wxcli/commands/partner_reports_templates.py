import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling partner-reports-templates.")


@app.command("list")
def cmd_list(
    service: str = typer.Option(None, "--service", help="List reports which use this service."),
    template_id: str = typer.Option(None, "--template-id", help="List reports with this report template ID."),
    from_param: str = typer.Option(None, "--from", help="List reports that were created on or after this date."),
    to: str = typer.Option(None, "--to", help="List reports that were created before this date."),
    region_id: str = typer.Option(None, "--region-id", help="Data in the report will be from organizations in this region"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Reports."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/reports"
    params = {}
    if service is not None:
        params["service"] = service
    if template_id is not None:
        params["templateId"] = template_id
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if region_id is not None:
        params["regionId"] = region_id
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
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
    items = result.get("reports", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    template_id: str = typer.Option(None, "--template-id", help=""),
    start_date: str = typer.Option(None, "--start-date", help=""),
    end_date: str = typer.Option(None, "--end-date", help=""),
    region_id: str = typer.Option(None, "--region-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Report."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/reports"
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
        if region_id is not None:
            body["regionId"] = region_id
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
    report_id: str = typer.Argument(help="reportId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Report Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/reports/{report_id}"
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
    url = f"https://webexapis.com/v1/partner/reports/{report_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {report_id}")



@app.command("list-templates")
def list_templates(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Report Templates."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/reports/templates"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
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
    items = result.get("templates", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


