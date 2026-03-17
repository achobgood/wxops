import typer
from typing import Optional
from wxc_sdk.telephony.callpark import CallPark
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling call park groups.")


@app.command("list")
def list_callparks(
    location_id: str = typer.Argument(help="Location ID"),
    name: Optional[str] = typer.Option(None, "--name", help="Filter by name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List call park groups for a location."""
    api = get_api(debug=debug)

    kwargs = dict(location_id=location_id)
    if name:
        kwargs["name"] = name

    callparks = list(api.telephony.callpark.list(**kwargs))

    if output == "json":
        print_json(callparks)
    else:
        print_table(
            callparks,
            columns=[
                ("ID", "callpark_id"),
                ("Name", "name"),
            ],
            limit=limit,
        )


@app.command("show")
def show_callpark(
    location_id: str = typer.Argument(help="Location ID"),
    callpark_id: str = typer.Argument(help="Call Park ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single call park group."""
    api = get_api(debug=debug)
    callpark = api.telephony.callpark.details(
        location_id=location_id,
        callpark_id=callpark_id,
    )
    print_json(callpark)


@app.command("create")
def create_callpark(
    location_id: str = typer.Argument(help="Location ID"),
    name: str = typer.Option(..., "--name", help="Call park group name"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new call park group for a location."""
    api = get_api(debug=debug)
    settings = CallPark(name=name)
    callpark_id = api.telephony.callpark.create(
        location_id=location_id,
        settings=settings,
    )
    typer.echo(f"Created: {callpark_id} ({name})")


@app.command("update")
def update_callpark(
    location_id: str = typer.Argument(help="Location ID"),
    callpark_id: str = typer.Argument(help="Call Park ID"),
    name: Optional[str] = typer.Option(None, "--name", help="New call park group name"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a call park group."""
    api = get_api(debug=debug)
    settings = CallPark(name=name)
    api.telephony.callpark.update(
        location_id=location_id,
        callpark_id=callpark_id,
        settings=settings,
    )
    typer.echo(f"Updated: {callpark_id}")


@app.command("delete")
def delete_callpark(
    location_id: str = typer.Argument(help="Location ID"),
    callpark_id: str = typer.Argument(help="Call Park ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a call park group."""
    api = get_api(debug=debug)

    if not force:
        typer.confirm(f"Delete call park {callpark_id}?", abort=True)

    api.telephony.callpark.delete_callpark(
        location_id=location_id,
        callpark_id=callpark_id,
    )
    typer.echo(f"Deleted: {callpark_id}")
