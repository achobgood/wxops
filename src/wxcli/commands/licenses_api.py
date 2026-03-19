import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling licenses.")


@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Licenses."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/licenses"
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
        print_table(items, columns=[('ID', 'id'), ('Name', 'name'), ('Total Units', 'totalUnits'), ('Consumed', 'consumedUnits')], limit=limit)



@app.command("show")
def show(
    license_id: str = typer.Argument(help="licenseId"),
    include_assigned_to: str = typer.Option(None, "--include-assigned-to", help="Choices: user"),
    next: str = typer.Option(None, "--next", help="List the next set of users. Applicable only if `includeAssig"),
    limit: str = typer.Option(None, "--limit", help="A limit on the number of users to be returned in the respons"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get License Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/licenses/{license_id}"
    params = {}
    if include_assigned_to is not None:
        params["includeAssignedTo"] = include_assigned_to
    if next is not None:
        params["next"] = next
    if limit is not None:
        params["limit"] = limit
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



@app.command("update")
def update(
    email: str = typer.Option(None, "--email", help="Email address of the user."),
    person_id: str = typer.Option(None, "--person-id", help="A unique identifier for the user."),
    org_id: str = typer.Option(None, "--org-id", help="The ID of the organization to which the licenses and siteUrl"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign Licenses to Users."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/licenses/users"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if email is not None:
            body["email"] = email
        if person_id is not None:
            body["personId"] = person_id
        if org_id is not None:
            body["orgId"] = org_id
    try:
        result = api.session.rest_patch(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")


