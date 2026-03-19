import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling webhooks.")


@app.command("list")
def cmd_list(
    max: str = typer.Option(None, "--max", help="Limit the maximum number of webhooks in the response."),
    owned_by: str = typer.Option(None, "--owned-by", help="Limit the result list to org wide webhooks. Only allowed val"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Webhooks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks"
    params = {}
    if max is not None:
        params["max"] = max
    if owned_by is not None:
        params["ownedBy"] = owned_by
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Target URL', 'targetUrl'), ('Resource', 'resource')], limit=limit)



@app.command("create")
def create(
    name: str = typer.Option(..., "--name", help="A user-friendly name for the webhook."),
    target_url: str = typer.Option(..., "--target-url", help="URL that receives POST requests for each event."),
    resource: str = typer.Option(..., "--resource", help="Resource type for the webhook. Creating a webhook requires ' (use --help for choices)"),
    event: str = typer.Option(..., "--event", help="Event type for the webhook.  * `created` - An object is crea (use --help for choices)"),
    filter_param: str = typer.Option(None, "--filter", help="Filter that defines the webhook scope. See [Filtering Webhoo"),
    secret: str = typer.Option(None, "--secret", help="Secret used to generate payload signature."),
    owned_by: str = typer.Option(None, "--owned-by", help="Specify `org` when creating an org/admin level webhook. Supp"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Webhook."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if target_url is not None:
            body["targetUrl"] = target_url
        if resource is not None:
            body["resource"] = resource
        if event is not None:
            body["event"] = event
        if filter_param is not None:
            body["filter"] = filter_param
        if secret is not None:
            body["secret"] = secret
        if owned_by is not None:
            body["ownedBy"] = owned_by
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
    webhook_id: str = typer.Argument(help="webhookId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Webhook Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks/{webhook_id}"
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
    webhook_id: str = typer.Argument(help="webhookId"),
    name: str = typer.Option(None, "--name", help="A user-friendly name for the webhook."),
    target_url: str = typer.Option(None, "--target-url", help="URL that receives POST requests for each event."),
    secret: str = typer.Option(None, "--secret", help="Secret used to generate payload signature."),
    owned_by: str = typer.Option(None, "--owned-by", help="Specify `org` when creating an org/admin level webhook. Supp"),
    status: str = typer.Option(None, "--status", help="Choices: active"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Webhook."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks/{webhook_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if target_url is not None:
            body["targetUrl"] = target_url
        if secret is not None:
            body["secret"] = secret
        if owned_by is not None:
            body["ownedBy"] = owned_by
        if status is not None:
            body["status"] = status
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
    webhook_id: str = typer.Argument(help="webhookId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Webhook."""
    if not force:
        typer.confirm(f"Delete {webhook_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks/{webhook_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {webhook_id}")


