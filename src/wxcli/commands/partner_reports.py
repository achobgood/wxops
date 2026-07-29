import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling partner-reports.")


@app.command("list", short_help="List Reports.")
def cmd_list(
    service: str = typer.Option(None, "--service", help="List reports which use this service."),
    template_id: str = typer.Option(None, "--template-id", help="List reports with this report template ID."),
    from_param: str = typer.Option(None, "--from", help="List reports that were created on or after this date."),
    to: str = typer.Option(None, "--to", help="List reports that were created before this date."),
    region_id: str = typer.Option(None, "--region-id", help="Data in the report will be from organizations in this region, for example, US, CA, or EU."),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("Report Attributes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Title', 'title'), ('Service', 'service'), ('Start Date', 'startDate'), ('End Date', 'endDate')], limit=limit)



_BODY_SKELETON_CREATE = '{"templateId":0,"startDate":"...","endDate":"...","regionId":"..."}'

@app.command("create", short_help="Create a Report.")
def create(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    template_id: str = typer.Option(None, "--template-id", help="(required) Unique ID representing valid report templates."),
    start_date: str = typer.Option(None, "--start-date", help="(required) Data in the report will be from this date onwards."),
    end_date: str = typer.Option(None, "--end-date", help="(required) Data in the report will be until this date."),
    region_id: str = typer.Option(None, "--region-id", help="Data in the report will be from organizations in this region, for example, US, CA, or EU."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Report.\n\n\b\nExample: wxcli partner-reports create --template-id TEMPLATE_ID --start-date START_DATE --end-date END_DATE\n\n\b\nExample --json-body: '{"templateId":0,"startDate":"...","endDate":"...","regionId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/reports"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    if json_body:
        body = load_json_body(json_body)
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
        _missing = [f for f in ['templateId', 'startDate', 'endDate'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



@app.command("show", short_help="Get Report Details.")
def show(
    report_id: str = typer.Argument(help="Webex REPORT id, from: wxcli partner-reports list"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Report Details.\n\n\b\nExample: wxcli partner-reports show REPORT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/reports/{report_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("delete", short_help="Delete a Report.")
def delete(
    report_id: str = typer.Argument(help="Webex REPORT id, from: wxcli partner-reports list"),
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Report.\n\n\b\nExample: wxcli partner-reports delete REPORT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {report_id}?", abort=True)
    url = f"https://webexapis.com/v1/partner/reports/{report_id}"
    params = {}
    if on_behalf_of_sub_partner_org_id is not None:
        params["onBehalfOfSubPartnerOrgId"] = on_behalf_of_sub_partner_org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {report_id}")
    else:
        emit({"status": "deleted", "id": report_id}, output=output, fields=fields)



@app.command("list-templates", short_help="List Report Templates.")
def list_templates(
    on_behalf_of_sub_partner_org_id: str = typer.Option(None, "--on-behalf-of-sub-partner-org-id", help="The encoded organization ID for the sub partner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("Template Collection", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Template ID', 'templateId'), ('Title', 'title'), ('Service', 'service'), ('Category', 'category'), ('Max Days', 'maxDays')], limit=limit)


