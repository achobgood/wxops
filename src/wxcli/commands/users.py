import typer
from wxc_sdk.people import Person

from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling users.")


@app.command("list")
def list_users(
    calling_enabled: bool = typer.Option(False, "--calling-enabled", help="Only calling-enabled users"),
    location_id: str = typer.Option(None, "--location", help="Filter by location ID"),
    email: str = typer.Option(None, "--email", help="Filter by email"),
    output: str = typer.Option("table", "--output", "-o"),
    limit: int = typer.Option(50, "--limit"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List users in the organization."""
    api = get_api(debug=debug)

    kwargs = {}
    if calling_enabled:
        kwargs["calling_data"] = True
    if email:
        kwargs["email"] = email

    users = list(api.people.list(**kwargs))

    if calling_enabled:
        users = [u for u in users if u.location_id]

    if location_id:
        users = [u for u in users if u.location_id == location_id]

    if output == "json":
        print_json(users)
    else:
        print_table(
            users,
            columns=[
                ("ID", "person_id"),
                ("Name", "display_name"),
                ("Email", "emails"),
                ("Location", "location_id"),
            ],
            limit=limit,
        )


@app.command("show")
def show_user(
    user_id: str = typer.Argument(help="User/Person ID"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single user."""
    api = get_api(debug=debug)
    person = api.people.details(person_id=user_id, calling_data=True)
    print_json(person)


@app.command("create")
def create_user(
    email: str = typer.Option(..., "--email"),
    first: str = typer.Option(..., "--first", help="First name"),
    last: str = typer.Option(..., "--last", help="Last name"),
    location_id: str = typer.Option(None, "--location", help="Location ID"),
    license_id: str = typer.Option(None, "--license", help="License ID (use 'wxcli licenses list')"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new user."""
    api = get_api(debug=debug)

    settings = Person(
        emails=[email],
        first_name=first,
        last_name=last,
    )
    if location_id:
        settings.location_id = location_id
    if license_id:
        settings.licenses = [license_id]

    person = api.people.create(settings=settings)

    if not license_id:
        typer.echo("Warning: User created without calling license. Use 'wxcli licenses list' to find one.", err=True)

    typer.echo(f"Created: {person.person_id} ({person.display_name})")


@app.command("update")
def update_user(
    user_id: str = typer.Argument(help="User/Person ID"),
    first: str = typer.Option(None, "--first"),
    last: str = typer.Option(None, "--last"),
    location_id: str = typer.Option(None, "--location"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a user."""
    api = get_api(debug=debug)
    person = api.people.details(person_id=user_id)
    if first:
        person.first_name = first
    if last:
        person.last_name = last
    if location_id:
        person.location_id = location_id
    api.people.update(person=person)
    typer.echo(f"Updated: {user_id}")


@app.command("delete")
def delete_user(
    user_id: str = typer.Argument(help="User/Person ID"),
    force: bool = typer.Option(False, "--force"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a user."""
    if not force:
        typer.confirm(f"Delete user {user_id}?", abort=True)
    api = get_api(debug=debug)
    api.people.delete_person(person_id=user_id)
    typer.echo(f"Deleted: {user_id}")
