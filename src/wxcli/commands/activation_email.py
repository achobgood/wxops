import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Admin: activation-email.")


@app.command("create", short_help="Initiate Bulk Activation Email Resend Job.")
def create(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Initiate Bulk Activation Email Resend Job."""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/jobs/sendActivationEmails"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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



@app.command("list", short_help="Get Bulk Activation Email Resend Job Status.")
def cmd_list(
    job_id: str = typer.Argument(help="Webex JOB_ID id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Bulk Activation Email Resend Job Status.\n\n\b\nExample: wxcli activation-email list JOB_ID"""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/jobs/sendActivationEmails/{job_id}/status"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-errors", short_help="Get Bulk Activation Email Resend Job Errors.")
def list_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Refused (exit 2): this endpoint ignores it, inferred from its spec, which declares no offset parameter. Use --all and slice the output, e.g. --fields '[2:5]'."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Bulk Activation Email Resend Job Errors.\n\n\b\nExample: wxcli activation-email list-errors JOB_ID"""
    if offset > 0:
        typer.echo("Error: this endpoint ignores --offset: its spec declares no offset parameter, and every such endpoint measured returned the first page again (ADR-18). Drop --offset and slice " + ("the --all output instead, e.g. --fields '[2:5]'." if all_pages else "every page instead, e.g. --all --fields '[2:5]'."), err=True)
        raise typer.Exit(2)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/jobs/sendActivationEmails/{job_id}/errors"
    params = {}
    if limit > 0:
        params["max"] = limit
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
    emit(items, output=output, fields=fields, columns=[('Tracking ID', 'trackingId'), ('Item Number', 'itemNumber')], limit=limit)


