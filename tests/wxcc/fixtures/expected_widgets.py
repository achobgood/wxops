import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_flow_store_base_url, get_cc_org_id
from wxcli.common import verify_write
from pathlib import Path


app = typer.Typer(help="Manage Webex Contact Center: widgets.")


@app.command("show", short_help="List widgets.")
def show(
    project_id: str = typer.Argument(help="projectId"),
    page: str = typer.Option(None, "--page", help=""),
    size: str = typer.Option(None, "--size", help=""),
    kind: str = typer.Option(None, "--kind", help="Choices: A, B"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List widgets.\n\n\b\nExample: wxcli widgets show PROJECT_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/widgets"
    params = {}
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if kind is not None:
        params["kind"] = kind
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"name":"...","count":0,"spec":{}}'

@app.command("create", short_help="Create a widget.")
def create(
    project_id: str = typer.Argument(help="projectId"),
    name: str = typer.Option(None, "--name", help="(required)"),
    count: str = typer.Option(None, "--count", help=""),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a widget.\n\n\b\nExample: wxcli widgets create PROJECT_ID --name NAME\n\n\b\nExample --json-body: '{"name":"...","count":0,"spec":{}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/widgets"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if count is not None:
            body["count"] = count
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
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



@app.command("get", short_help="Get a widget.")
def get(
    project_id: str = typer.Argument(help="projectId"),
    widget_id: str = typer.Argument(help="widgetId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a widget.\n\n\b\nExample: wxcli widgets get PROJECT_ID WIDGET_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/widgets/{widget_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("merge-patch", short_help="Merge-patch a widget (no-op).", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def merge_patch(ctx: typer.Context):
    """Merge-patch a widget (no-op).\n\nBLOCKED: no-op; use update"""
    typer.echo('no-op; use update', err=True)
    raise typer.Exit(2)



@app.command("delete", short_help="Delete a widget.")
def delete(
    project_id: str = typer.Argument(help="projectId"),
    widget_id: str = typer.Argument(help="widgetId"),
    force: str = typer.Option(None, "--force", help=""),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a widget.\n\n\b\nExample: wxcli widgets delete PROJECT_ID WIDGET_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {widget_id}?", abort=True)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/widgets/{widget_id}"
    params = {}
    if force is not None:
        params["force"] = force
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {widget_id}")
    else:
        emit({"status": "deleted", "id": widget_id}, output=output, fields=fields)



@app.command("import", short_help="Import a widget.")
def cmd_import(
    project_id: str = typer.Argument(help="projectId"),
    flow_type: str = typer.Option(None, "--flow-type", help=""),
    overwrite: str = typer.Option(None, "--overwrite", help=""),
    file: Path = typer.Option(..., "--file", exists=True, dir_okay=False, readable=True, help="Path of the file to upload, sent as the multipart 'file' part."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Import a widget.\n\n\b\nExample: wxcli widgets import PROJECT_ID --file FILE"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/widgets:import"
    params = {}
    if flow_type is not None:
        params["Flow Type"] = flow_type
    if overwrite is not None:
        params["overwrite"] = overwrite
    try:
        result = api.session.rest_post_multipart(url, files={"file": (Path(file).name, Path(file).read_bytes(), "application/json")}, params=params)
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



@app.command("refresh", short_help="Refresh widgets.")
def refresh(
    project_id: str = typer.Argument(help="projectId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Refresh widgets.\n\n\b\nExample: wxcli widgets refresh PROJECT_ID"""
    typer.echo('Warning: may be slow on big orgs', err=True)
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/widgets:refresh"
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


