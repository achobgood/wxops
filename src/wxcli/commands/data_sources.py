import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling data-sources.")


_BODY_SKELETON_CREATE = '{"audience":"...","nonce":"...","schemaId":"...","subject":"...","tokenLifetimeMinutes":0,"url":"..."}'

@app.command("create", short_help="Register a Data Source.")
def create(
    audience: str = typer.Option(None, "--audience", help="The audience field in the JWT token. Usually, the DAPs app name."),
    nonce: str = typer.Option(None, "--nonce", help="Unique nonce used in the encryption of the JWT token."),
    schema_id: str = typer.Option(None, "--schema-id", help="The schema id used for the data exchange."),
    subject: str = typer.Option(None, "--subject", help="Rhe subject field in the JWT token. Usually, an indication of the app's function"),
    token_lifetime_minutes: str = typer.Option(None, "--token-lifetime-minutes", help="The validity of the created token in minutes. Before the token expiration time, a new token must be provided, or Webex will stop delivering data after the token expiration. Must be equal or less to 1440."),
    url: str = typer.Option(None, "--url", help="The URL of the endpoint where Webex will send the data."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Register a Data Source.\n\n\b\nExample --json-body: '{"audience":"...","nonce":"...","schemaId":"...","subject":"...","tokenLifetimeMinutes":0,"url":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if audience is not None:
            body["audience"] = audience
        if nonce is not None:
            body["nonce"] = nonce
        if schema_id is not None:
            body["schemaId"] = schema_id
        if subject is not None:
            body["subject"] = subject
        if token_lifetime_minutes is not None:
            body["tokenLifetimeMinutes"] = token_lifetime_minutes
        if url is not None:
            body["url"] = url
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



@app.command("list", short_help="Retrieve All Data Sources.")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve All Data Sources."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/"
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



@app.command("list-schemas", short_help="Retrieve Data Source Schemas.")
def list_schemas(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Data Source Schemas."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/schemas"
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



@app.command("show", short_help="Retrieve Details of a Specific Data Source Schema.")
def show(
    schema_id: str = typer.Argument(help="UUID, from: wxcli cc-data-sources list-schemas"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Details of a Specific Data Source Schema.\n\n\b\nExample: wxcli data-sources show SCHEMA_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/schemas/{schema_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-data-sources", short_help="Retrieve Data Source Details.")
def show_data_sources(
    data_source_id: str = typer.Argument(help="UUID, from: wxcli cc-data-sources list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Data Source Details.\n\n\b\nExample: wxcli data-sources show-data-sources DATA_SOURCE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/{data_source_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"audience":"...","errorMessage":"...","nonce":"...","schemaId":"...","status":"...","subject":"...","tokenLifetimeMinutes":0,"url":"..."}'

@app.command("update", short_help="Update a Data Source.")
def update(
    data_source_id: str = typer.Argument(help="UUID, from: wxcli cc-data-sources list"),
    audience: str = typer.Option(None, "--audience", help="The audience field in the JWT token. Usually, the DAPs app name."),
    error_message: str = typer.Option(None, "--error-message", help="Error Message shown in Control Hub when status is set to `disabled`."),
    nonce: str = typer.Option(None, "--nonce", help="Unique nonce used in the encryption of the JWT token."),
    schema_id: str = typer.Option(None, "--schema-id", help="The schema id used for the data exchange."),
    status: str = typer.Option(None, "--status", help="The status of the Data Source; `active` or `disabled`."),
    subject: str = typer.Option(None, "--subject", help="The subject field in the JWT token. Usually, an indication of the app's function"),
    token_lifetime_minutes: str = typer.Option(None, "--token-lifetime-minutes", help="The validity of the created token in minutes. Before the token expiration time, a new token must be provided, or Webex will stop delivering data after the token expiration. Must be equal or less to 1440."),
    url: str = typer.Option(None, "--url", help="The URL of the endpoint where Webex will send the data."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Data Source.\n\n\b\nExample: wxcli data-sources update DATA_SOURCE_ID\n\n\b\nExample --json-body: '{"audience":"...","errorMessage":"...","nonce":"...","schemaId":"...","status":"...","subject":"...","tokenLifetimeMinutes":0,"url":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/{data_source_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if audience is not None:
            body["audience"] = audience
        if error_message is not None:
            body["errorMessage"] = error_message
        if nonce is not None:
            body["nonce"] = nonce
        if schema_id is not None:
            body["schemaId"] = schema_id
        if status is not None:
            body["status"] = status
        if subject is not None:
            body["subject"] = subject
        if token_lifetime_minutes is not None:
            body["tokenLifetimeMinutes"] = token_lifetime_minutes
        if url is not None:
            body["url"] = url
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
        emit({"status": "updated", "id": data_source_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Data Source.")
def delete(
    data_source_id: str = typer.Argument(help="UUID, from: wxcli cc-data-sources list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Data Source.\n\n\b\nExample: wxcli data-sources delete DATA_SOURCE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {data_source_id}?", abort=True)
    url = f"https://webexapis.com/v1/dataSources/{data_source_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {data_source_id}")
    else:
        emit({"status": "deleted", "id": data_source_id}, output=output, fields=fields)


