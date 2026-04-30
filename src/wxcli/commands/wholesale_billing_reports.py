import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling wholesale-billing-reports.")


@app.command("list")
def cmd_list(
    billing_start_date: str = typer.Option(None, "--billing-start-date", help="Only include billing reports having this billing `startDate`"),
    billing_end_date: str = typer.Option(None, "--billing-end-date", help="Only include billing reports having this billing `endDate`."),
    type_param: str = typer.Option(None, "--type", help="Choices: PARTNER, CUSTOMER, USER"),
    sort_by: str = typer.Option(None, "--sort-by", help="Choices: id, billingStartDate, billingEndDate, status"),
    status: str = typer.Option(None, "--status", help="Choices: IN_PROGRESS, COMPLETED, FAILED"),
    sub_partner_org_id: str = typer.Option(None, "--sub-partner-org-id", help="The Organization ID of the sub partner on Cisco Webex."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Wholesale Billing Reports."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/billing/reports"
    params = {}
    if billing_start_date is not None:
        params["billingStartDate"] = billing_start_date
    if billing_end_date is not None:
        params["billingEndDate"] = billing_end_date
    if type_param is not None:
        params["type"] = type_param
    if sort_by is not None:
        params["sortBy"] = sort_by
    if status is not None:
        params["status"] = status
    if sub_partner_org_id is not None:
        params["subPartnerOrgId"] = sub_partner_org_id
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
    billing_start_date: str = typer.Option(None, "--billing-start-date", help="(required) The `startDate` (`YYYY-MM-DD`) for which the partner request"),
    billing_end_date: str = typer.Option(None, "--billing-end-date", help="(required) The `endDate` (`YYYY-MM-DD`) for which the partner requests"),
    type_param: str = typer.Option(None, "--type", help="Create report of the given type, `PARTNER`, `CUSTOMER`, or `"),
    sub_partner_org_id: str = typer.Option(None, "--sub-partner-org-id", help="The Organization ID of the sub partner on Cisco Webex."),
    internal: bool = typer.Option(None, "--internal/--no-internal", help="If true or selected, internal orgs will be included in the b"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Wholesale Billing Report."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/billing/reports"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if billing_start_date is not None:
            body["billingStartDate"] = billing_start_date
        if billing_end_date is not None:
            body["billingEndDate"] = billing_end_date
        if type_param is not None:
            body["type"] = type_param
        if sub_partner_org_id is not None:
            body["subPartnerOrgId"] = sub_partner_org_id
        if internal is not None:
            body["internal"] = internal
        _missing = [f for f in ['billingStartDate', 'billingEndDate'] if f not in body or body[f] is None]
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
    """Get a Wholesale Billing Report."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/billing/reports/{id}"
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
    """Delete a Wholesale Billing Report."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/wholesale/billing/reports/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {id}")


