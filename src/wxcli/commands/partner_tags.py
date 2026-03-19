import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling partner-tags.")


@app.command("show")
def show(
    type_param: str = typer.Option(..., "--type", help="List tags associated with an organization."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve all customer tags."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/tags"
    params = {}
    if type_param is not None:
        params["type"] = type_param
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("create")
def create(
    org_id: str = typer.Argument(help="orgId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create or Replace existing customer tags with the provided ones."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/tags/organizations/{org_id}/assignTags"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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



@app.command("show-organizations-tags")
def show_organizations_tags(
    org_id: str = typer.Argument(help="orgId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get customer organization's tags."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/tags/organizations/{org_id}"
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



@app.command("show-organizations-tags-1")
def show_organizations_tags_1(
    tags: str = typer.Option(..., "--tags", help="A comma separated list of tags to filter by."),
    max: str = typer.Option(None, "--max", help="Value must be between 1 and 100, inclusive."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch all customers for a given set of tags."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/tags/organizations"
    params = {}
    if tags is not None:
        params["tags"] = tags
    if max is not None:
        params["max"] = max
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("create-assign-tags")
def create_assign_tags(
    org_id: str = typer.Argument(help="orgId"),
    subscription_id: str = typer.Argument(help="subscriptionId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create or Replace existing subscription tags with the provided ones."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/tags/organizations/{org_id}/subscriptions/{subscription_id}/assignTags"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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



@app.command("show-subscriptions-tags")
def show_subscriptions_tags(
    tags: str = typer.Option(..., "--tags", help="A comma separated list of tags to filter by."),
    max: str = typer.Option(None, "--max", help="Value must be between 1 and 100, inclusive."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Subscription List on a given tag name or a set of tags."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/tags/subscriptions"
    params = {}
    if tags is not None:
        params["tags"] = tags
    if max is not None:
        params["max"] = max
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("show-subscriptions-organizations")
def show_subscriptions_organizations(
    org_id: str = typer.Argument(help="orgId"),
    subscription_id: str = typer.Argument(help="subscriptionId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch a Subscription."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/partner/tags/organizations/{org_id}/subscriptions/{subscription_id}"
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


