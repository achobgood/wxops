import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling: export-schedule-usage-jobs.")


@app.command("list", short_help="List Export Schedule Usage Jobs.")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Export Schedule Usage Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/schedules/exportUsage"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Tracking ID', 'trackingId'), ('Source User ID', 'sourceUserId'), ('Source Customer ID', 'sourceCustomerId')], limit=limit)



_BODY_SKELETON_CREATE = '{"level":"LOCATION","locationId":"...","scheduleId":"...","type":"businessHours"}'

@app.command("create", short_help="Create Export Schedule Usage Job.")
def create(
    level: str = typer.Option(None, "--level", help="(required) Choices: LOCATION"),
    location_id: str = typer.Option(None, "--location-id", help="(required) Encoded LOCATION ID. For ORGANIZATION, omission or null applies no location filter; a supplied non-null value must be nonblank. For LOCATION, this field is required, non-null and nonblank, and identifies the schedule's location."),
    schedule_id: str = typer.Option(None, "--schedule-id", help="(required) Encoded SCHEDULE ID identifying the single schedule whose usage is exported."),
    type_param: str = typer.Option(None, "--type", help="(required) Choices: businessHours, holidays"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Export Schedule Usage Job.\n\n\b\nExample: wxcli export-schedule-usage-jobs create --level LOCATION --location-id LOCATION_ID --schedule-id SCHEDULE_ID --type businessHours\n\n\b\nExample --json-body: '{"level":"LOCATION","locationId":"...","scheduleId":"...","type":"businessHours"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/schedules/exportUsage"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if level is not None:
            body["level"] = level
        if location_id is not None:
            body["locationId"] = location_id
        if schedule_id is not None:
            body["scheduleId"] = schedule_id
        if type_param is not None:
            body["type"] = type_param
        _missing = [f for f in ['level', 'locationId', 'scheduleId', 'type'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Export Schedule Usage Job Status.")
def show(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli export-schedule-usage-jobs list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Export Schedule Usage Job Status.\n\n\b\nExample: wxcli export-schedule-usage-jobs show JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/schedules/exportUsage/{job_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("pause-export-schedule", short_help="Pause Export Schedule Usage Job.")
def pause_export_schedule(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli export-schedule-usage-jobs list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Pause Export Schedule Usage Job.\n\n\b\nExample: wxcli export-schedule-usage-jobs pause-export-schedule JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/schedules/exportUsage/{job_id}/actions/pause/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("resume-export-schedule", short_help="Resume Export Schedule Usage Job.")
def resume_export_schedule(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli export-schedule-usage-jobs list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Resume Export Schedule Usage Job.\n\n\b\nExample: wxcli export-schedule-usage-jobs resume-export-schedule JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/schedules/exportUsage/{job_id}/actions/resume/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-errors", short_help="List Export Schedule Usage Job Errors.")
def list_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli export-schedule-usage-jobs list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Refused (exit 2): this endpoint ignores it, inferred from its spec, which declares no offset parameter. Use --all and slice the output, e.g. --fields '[2:5]'."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Export Schedule Usage Job Errors.\n\n\b\nExample: wxcli export-schedule-usage-jobs list-errors JOB_ID"""
    if offset > 0:
        typer.echo("Error: this endpoint ignores --offset: its spec declares no offset parameter, and every such endpoint measured returned the first page again (ADR-18). Drop --offset and slice " + ("the --all output instead, e.g. --fields '[2:5]'." if all_pages else "every page instead, e.g. --all --fields '[2:5]'."), err=True)
        raise typer.Exit(2)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/schedules/exportUsage/{job_id}/errors"
    params = {}
    if limit > 0:
        params["max"] = limit
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params, remedies=("all",))
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('Tracking ID', 'trackingId'), ('Item Number', 'itemNumber'), ('Item', 'item'), ('Error Type', 'errorType')], limit=limit)


