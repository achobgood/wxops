import typer
from typing import Optional
from wxc_sdk.telephony.callpickup import CallPickup
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling call pickup groups.")


@app.command("list")
def list_pickups(
    location_id: str = typer.Argument(help="Location ID"),
    name: Optional[str] = typer.Option(None, "--name", help="Filter by name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List call pickup groups for a location."""
    api = get_api(debug=debug)

    kwargs = dict(location_id=location_id)
    if name:
        kwargs["name"] = name

    pickups = list(api.telephony.pickup.list(**kwargs))

    if output == "json":
        print_json(pickups)
    else:
        print_table(
            pickups,
            columns=[
                ("ID", "pickup_id"),
                ("Name", "name"),
            ],
            limit=limit,
        )


@app.command("show")
def show_pickup(
    location_id: str = typer.Argument(help="Location ID"),
    pickup_id: str = typer.Argument(help="Call Pickup ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single call pickup group."""
    api = get_api(debug=debug)
    pickup = api.telephony.pickup.details(
        location_id=location_id,
        pickup_id=pickup_id,
    )
    print_json(pickup)


@app.command("create")
def create_pickup(
    location_id: str = typer.Argument(help="Location ID"),
    name: str = typer.Option(..., "--name", help="Call pickup group name"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new call pickup group for a location."""
    api = get_api(debug=debug)
    settings = CallPickup(name=name)
    pickup_id = api.telephony.pickup.create(
        location_id=location_id,
        settings=settings,
    )
    typer.echo(f"Created: {pickup_id} ({name})")


@app.command("update")
def update_pickup(
    location_id: str = typer.Argument(help="Location ID"),
    pickup_id: str = typer.Argument(help="Call Pickup ID"),
    name: Optional[str] = typer.Option(None, "--name", help="New call pickup group name"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a call pickup group."""
    api = get_api(debug=debug)
    settings = CallPickup(name=name)
    api.telephony.pickup.update(
        location_id=location_id,
        pickup_id=pickup_id,
        settings=settings,
    )
    typer.echo(f"Updated: {pickup_id}")


@app.command("delete")
def delete_pickup(
    location_id: str = typer.Argument(help="Location ID"),
    pickup_id: str = typer.Argument(help="Call Pickup ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a call pickup group."""
    api = get_api(debug=debug)

    if not force:
        typer.confirm(f"Delete call pickup {pickup_id}?", abort=True)

    api.telephony.pickup.delete_pickup(
        location_id=location_id,
        pickup_id=pickup_id,
    )
    typer.echo(f"Deleted: {pickup_id}")
