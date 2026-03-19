import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling data-sources.")


@app.command("create")
def create(
    audience: str = typer.Option(None, "--audience", help="The audience field in the JWT token. Usually, the DAPs app n"),
    nonce: str = typer.Option(None, "--nonce", help="Unique nonce used in the encryption of the JWT token."),
    schema_id: str = typer.Option(None, "--schema-id", help="The schema id used for the data exchange."),
    subject: str = typer.Option(None, "--subject", help="Rhe subject field in the JWT token. Usually, an indication o"),
    token_lifetime_minutes: str = typer.Option(None, "--token-lifetime-minutes", help="The validity of the created token in minutes. Before the tok"),
    url: str = typer.Option(None, "--url", help="The URL of the endpoint where Webex will send the data."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Register a Data Source."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources"
    if json_body:
        body = json.loads(json_body)
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



@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-schemas")
def list_schemas(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    schema_id: str = typer.Argument(help="schemaId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Details of a Specific Data Source Schema."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/schemas/{schema_id}"
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



@app.command("show-data-sources")
def show_data_sources(
    data_source_id: str = typer.Argument(help="dataSourceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve Data Source Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/{data_source_id}"
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



@app.command("update")
def update(
    data_source_id: str = typer.Argument(help="dataSourceId"),
    audience: str = typer.Option(None, "--audience", help="The audience field in the JWT token. Usually, the DAPs app n"),
    error_message: str = typer.Option(None, "--error-message", help="Error Message shown in Control Hub when status is set to `di"),
    nonce: str = typer.Option(None, "--nonce", help="Unique nonce used in the encryption of the JWT token."),
    schema_id: str = typer.Option(None, "--schema-id", help="The schema id used for the data exchange."),
    status: str = typer.Option(None, "--status", help="The status of the Data Source; `active` or `disabled`."),
    subject: str = typer.Option(None, "--subject", help="The subject field in the JWT token. Usually, an indication o"),
    token_lifetime_minutes: str = typer.Option(None, "--token-lifetime-minutes", help="The validity of the created token in minutes. Before the tok"),
    url: str = typer.Option(None, "--url", help="The URL of the endpoint where Webex will send the data."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Data Source."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/{data_source_id}"
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    data_source_id: str = typer.Argument(help="dataSourceId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Data Source."""
    if not force:
        typer.confirm(f"Delete {data_source_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dataSources/{data_source_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {data_source_id}")


