import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling broadworks-enterprises.")


@app.command("show")
def show(
    sp_enterprise_id: str = typer.Option(None, "--sp-enterprise-id", help="The Service Provider supplied unique identifier for the subscriber's enterprise."),
    starts_with: str = typer.Option(None, "--starts-with", help="The starting string of the enterprise identifiers to match against."),
    max: str = typer.Option(None, "--max", help="Limit the number of enterprises returned in the search, up to 1000."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List BroadWorks Enterprises."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/enterprises"
    params = {}
    if sp_enterprise_id is not None:
        params["spEnterpriseId"] = sp_enterprise_id
    if starts_with is not None:
        params["startsWith"] = starts_with
    if max is not None:
        params["max"] = max
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-broadworks-directory-sync")
def show_broadworks_directory_sync(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Directory Sync Status for an Enterprise."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/enterprises/{id}/broadworksDirectorySync"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"syncStatus":"..."}'

@app.command("create")
def create(
    id: str = typer.Argument(help="id"),
    sync_status: str = typer.Option(None, "--sync-status", help="(required) At this time, the only value allowed for this attribute is `SYNC_NOW` which will trigger the directory sync for the BroadWorks enterprise."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Trigger Directory Sync for an Enterprise\n\nExample --json-body:\n  '{"syncStatus":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/enterprises/{id}/broadworksDirectorySync"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if sync_status is not None:
            body["syncStatus"] = sync_status
        _missing = [f for f in ['syncStatus'] if f not in body or body[f] is None]
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



_BODY_SKELETON_UPDATE = '{"enableDirSync":true}'

@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    enable_dir_sync: bool = typer.Option(None, "--enable-dir-sync/--no-enable-dir-sync", help="The toggle to enable/disable directory sync."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Directory Sync for a BroadWorks Enterprise\n\nExample --json-body:\n  '{"enableDirSync":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/enterprises/{id}/broadworksDirectorySync"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enable_dir_sync is not None:
            body["enableDirSync"] = enable_dir_sync
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_EXTERNAL_USER = '{"userId":"..."}'

@app.command("create-external-user")
def create_external_user(
    id: str = typer.Argument(help="id"),
    user_id: str = typer.Option(None, "--user-id", help="The user ID of the Broadworks user to be synced (A non-webex user)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Trigger Directory Sync for a User\n\nExample --json-body:\n  '{"userId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_EXTERNAL_USER), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/enterprises/{id}/broadworksDirectorySync/externalUser"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if user_id is not None:
            body["userId"] = user_id
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


