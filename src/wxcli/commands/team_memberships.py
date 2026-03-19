import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling team-memberships.")


@app.command("list")
def cmd_list(
    team_id: str = typer.Option(None, "--team-id", help="List memberships for a team, by ID."),
    max: str = typer.Option(None, "--max", help="Limit the maximum number of team memberships in the response"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Team Memberships."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/team/memberships"
    params = {}
    if team_id is not None:
        params["teamId"] = team_id
    if max is not None:
        params["max"] = max
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



@app.command("create")
def create(
    team_id: str = typer.Option(..., "--team-id", help="The team ID."),
    person_id: str = typer.Option(None, "--person-id", help="The person ID."),
    person_email: str = typer.Option(None, "--person-email", help="The email address of the person."),
    is_moderator: bool = typer.Option(None, "--is-moderator/--no-is-moderator", help="Whether or not the participant is a team moderator."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Team Membership."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/team/memberships"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if team_id is not None:
            body["teamId"] = team_id
        if person_id is not None:
            body["personId"] = person_id
        if person_email is not None:
            body["personEmail"] = person_email
        if is_moderator is not None:
            body["isModerator"] = is_moderator
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
    membership_id: str = typer.Argument(help="membershipId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Team Membership Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/team/memberships/{membership_id}"
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
    membership_id: str = typer.Argument(help="membershipId"),
    is_moderator: bool = typer.Option(None, "--is-moderator/--no-is-moderator", help="Whether or not the participant is a team moderator."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Team Membership."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/team/memberships/{membership_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if is_moderator is not None:
            body["isModerator"] = is_moderator
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
    membership_id: str = typer.Argument(help="membershipId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Team Membership."""
    if not force:
        typer.confirm(f"Delete {membership_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/team/memberships/{membership_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {membership_id}")


