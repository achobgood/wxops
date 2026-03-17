import typer
from wxc_sdk.telephony.paging import Paging
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling paging groups.")


@app.command("list")
def list_paging(
    location_id: str = typer.Option(None, "--location", help="Filter by location ID"),
    name: str = typer.Option(None, "--name", help="Filter by name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List paging groups in the organization."""
    api = get_api(debug=debug)
    paging_groups = list(api.telephony.paging.list(
        location_id=location_id,
        name=name,
    ))
    if output == "json":
        print_json(paging_groups)
    else:
        print_table(
            paging_groups,
            columns=[
                ("ID", "paging_id"),
                ("Name", "name"),
                ("Extension", "extension"),
                ("Enabled", "enabled"),
            ],
            limit=limit,
        )


@app.command("show")
def show_paging(
    location_id: str = typer.Argument(help="Location ID"),
    paging_id: str = typer.Argument(help="Paging group ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single paging group."""
    api = get_api(debug=debug)
    pg = api.telephony.paging.details(location_id=location_id, paging_id=paging_id)
    print_json(pg)


@app.command("create")
def create_paging(
    location_id: str = typer.Option(..., "--location", help="Location ID"),
    name: str = typer.Option(..., "--name", help="Paging group name"),
    extension: str = typer.Option(..., "--extension", help="Extension number"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable paging group"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new paging group."""
    api = get_api(debug=debug)
    settings = Paging(
        name=name,
        extension=extension,
        enabled=enabled,
    )
    pg_id = api.telephony.paging.create(location_id=location_id, settings=settings)
    typer.echo(f"Created: {pg_id} ({name})")


@app.command("update")
def update_paging(
    location_id: str = typer.Argument(help="Location ID"),
    paging_id: str = typer.Argument(help="Paging group ID"),
    name: str = typer.Option(None, "--name", help="New name"),
    extension: str = typer.Option(None, "--extension", help="New extension"),
    enabled: bool = typer.Option(None, "--enabled/--disabled", help="Enable or disable"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a paging group."""
    api = get_api(debug=debug)
    pg = api.telephony.paging.details(location_id=location_id, paging_id=paging_id)
    if name is not None:
        pg.name = name
    if extension is not None:
        pg.extension = extension
    if enabled is not None:
        pg.enabled = enabled
    api.telephony.paging.update(location_id=location_id, update=pg, paging_id=paging_id)
    typer.echo(f"Updated: {paging_id}")


@app.command("delete")
def delete_paging(
    location_id: str = typer.Argument(help="Location ID"),
    paging_id: str = typer.Argument(help="Paging group ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a paging group."""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete paging group {paging_id}?", abort=True)
    api.telephony.paging.delete_paging(location_id=location_id, paging_id=paging_id)
    typer.echo(f"Deleted: {paging_id}")
