import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Calling usage-reports.")


@app.command("list", hidden=True)
@app.command("list-resource-types", short_help="Get available resource types.")
def list_resource_types(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get available resource types."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v1/usage-reports/resource-types"
    params = {}
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
    emit(items, output=output, fields=fields, columns=[('Display Name', 'displayName'), ('Resource Type', 'resourceType'), ('Description', 'description'), ('Data Start Date', 'dataStartDate'), ('Data End Date', 'dataEndDate')], limit=limit)



@app.command("list-usage-reports", short_help="List usage reports.")
def list_usage_reports(
    resource_type: str = typer.Option(None, "--resource-type", help="Filter by resource type"),
    created_after: str = typer.Option(None, "--created-after", help="Filter reports created after this timestamp (ISO 8601 format)"),
    created_before: str = typer.Option(None, "--created-before", help="Filter reports created before this timestamp (ISO 8601 format)"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List usage reports."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v1/usage-reports"
    params = {}
    if resource_type is not None:
        params["resourceType"] = resource_type
    if created_after is not None:
        params["createdAfter"] = created_after
    if created_before is not None:
        params["createdBefore"] = created_before
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
    emit(items, output=output, fields=fields, columns=[('Report ID', 'reportId'), ('Resource Type', 'resourceType'), ('Status', 'status'), ('Created Time', 'createdTime'), ('Completed Time', 'completedTime')], limit=limit)



_BODY_SKELETON_CREATE = '{"resourceType":"...","startDate":"...","endDate":"..."}'

@app.command("create", short_help="Create usage report.")
def create(
    resource_type: str = typer.Option(None, "--resource-type", help="Type of resource this report contains."),
    start_date: str = typer.Option(None, "--start-date", help="Report start date (inclusive), in yyyy-MM-dd format."),
    end_date: str = typer.Option(None, "--end-date", help="Report end date (exclusive), in yyyy-MM-dd format."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create usage report.\n\n\b\nExample --json-body: '{"resourceType":"...","startDate":"...","endDate":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v1/usage-reports"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if resource_type is not None:
            body["resourceType"] = resource_type
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
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



@app.command("show", short_help="Get usage report details.")
def show(
    report_id: str = typer.Argument(help="from: wxcli usage-reports list-usage-reports"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get usage report details.\n\n\b\nExample: wxcli usage-reports show REPORT_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v1/usage-reports/{report_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("delete", short_help="Delete usage report.")
def delete(
    report_id: str = typer.Argument(help="from: wxcli usage-reports list-usage-reports"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete usage report.\n\n\b\nExample: wxcli usage-reports delete REPORT_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {report_id}?", abort=True)
    url = f"{cc_base_url}/v1/usage-reports/{report_id}"
    try:
        result = api.session.rest_delete(url)
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



@app.command("list-download", short_help="Download usage report file.")
def list_download(
    file_id: str = typer.Argument(help="from: wxcli usage-reports list-usage-reports"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Download usage report file.\n\n\b\nExample: wxcli usage-reports list-download FILE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v1/usage-reports/{file_id}/download"
    params = {}
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
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


